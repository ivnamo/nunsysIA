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
                        "metadata": {"filename": "contrato.pdf"},
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
        },
    }
