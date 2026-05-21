from app.core.traceability import (
    build_public_data_summary,
    sanitize_failure_reason,
    sanitize_reasoning,
    sanitize_tool_calls,
)
from app.core.tracing import ToolCallTrace


def test_sanitize_tool_calls_redacts_sensitive_args_and_errors() -> None:
    tool_calls = [
        ToolCallTrace(
            tool="ERPTool",
            action="calculate_order_amount",
            args={
                "customer_id": "ALFKI",
                "database_url": "postgresql://user:pass@localhost/db",
                "nested": {"api_key": "secret-value"},
            },
            status="error",
            error="Connection failed for postgresql://user:pass@localhost/db",
            source="ERP",
        )
    ]

    sanitized = sanitize_tool_calls(tool_calls)

    assert sanitized[0].args == {
        "customer_id": "ALFKI",
        "database_url": "[redacted]",
        "nested": {"api_key": "[redacted]"},
    }
    assert sanitized[0].action == "calculate_order_amount"
    assert sanitized[0].error == "[redacted]"


def test_sanitize_reasoning_keeps_visible_steps_short() -> None:
    reasoning = ["  Consulta ERP   de pedidos pendientes  ", "x" * 300]

    sanitized = sanitize_reasoning(reasoning)

    assert sanitized[0] == "Consulta ERP de pedidos pendientes"
    assert sanitized[1].endswith("...")
    assert len(sanitized[1]) == 240


def test_sanitize_failure_reason_strips_connection_strings() -> None:
    assert (
        sanitize_failure_reason("fallo con postgresql+psycopg://user:pass@host/db")
        == "[redacted]"
    )


def test_build_public_data_summary_does_not_return_raw_rows() -> None:
    summary = build_public_data_summary(
        {
            "erp_orders": [
                {"order_id": 10248, "customer_id": "ALFKI", "amount": "440.00"},
                {"order_id": 10252, "customer_id": "ALFKI", "amount": "1863.00"},
            ],
            "production_by_order": {
                10248: {"order_id": 10248, "production_status": "in_progress"},
                10252: {"order_id": 10252, "production_status": "blocked"},
            },
            "rag": {
                "status": "completed",
                "chunks": [
                    {
                        "text": "contenido interno",
                        "metadata": {
                            "filename": "contrato.pdf",
                            "page": 2,
                            "chunk_id": "doc_123_p2_c1",
                        },
                        "score": 0.876543,
                    }
                ],
            },
        }
    )

    assert summary == {
        "erp_orders_count": 2,
        "erp_order_ids": [10248, 10252],
        "production_statuses_count": 2,
        "rag": {
            "status": "completed",
            "chunks_count": 1,
            "documents": ["contrato.pdf"],
            "citations": [
                {
                    "filename": "contrato.pdf",
                    "page": 2,
                    "chunk_id": "doc_123_p2_c1",
                    "score": 0.8765,
                }
            ],
        },
    }


def test_build_public_data_summary_includes_memory_summary_without_turn_text() -> None:
    summary = build_public_data_summary(
        {
            "memory": {
                "status": "found",
                "turns": [
                    {
                        "question": "Que pedidos pendientes tiene ALFKI?",
                        "answer": "El cliente ALFKI tiene 2 pedidos pendientes.",
                    }
                ],
                "facts": {"customer_id": "ALFKI", "order_ids": [10248, 10252]},
            }
        }
    )

    assert summary == {
        "memory": {
            "status": "found",
            "turns_count": 1,
            "customer_id": "ALFKI",
            "order_ids": [10248, 10252],
        }
    }


def test_build_public_data_summary_includes_economic_impact_without_raw_lines() -> None:
    summary = build_public_data_summary(
        {
            "order_amounts": [
                {"order_id": 10252, "amount": "1863.00"},
                {"order_id": 10248, "amount": "440.00"},
            ]
        }
    )

    assert summary == {
        "order_amounts_count": 2,
        "order_amount_order_ids": [10252, 10248],
        "economic_impact_total": "2303.00",
    }


def test_build_public_data_summary_includes_sanitized_replanning_events() -> None:
    summary = build_public_data_summary(
        {
            "replanning": [
                {
                    "attempt": 1,
                    "decision": "replan",
                    "status": "partial_answer",
                    "failure_reason": (
                        "Faltan fuentes obligatorias: Produccion. "
                        "postgresql://user:pass@localhost/db"
                    ),
                    "max_replans": 2,
                    "raw_plan": {"unsafe": "not public"},
                }
            ]
        }
    )

    assert summary == {
        "replanning": {
            "replans_count": 1,
            "max_replans": 2,
            "events": [
                {
                    "attempt": 1,
                    "decision": "replan",
                    "status": "partial_answer",
                    "failure_reason": "[redacted]",
                    "max_replans": 2,
                }
            ],
        }
    }
