from app.agents.validator import ValidatorNode
from app.core.tracing import ToolCallTrace


def test_validator_finishes_when_expected_sources_and_traces_exist() -> None:
    validator = ValidatorNode()

    state = validator(
        {
            "plan": {
                "intent": "erp",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "ERPTool",
                        "action": "get_pending_orders_by_customer",
                        "args": {"customer_id": "ALFKI"},
                        "required": True,
                    }
                ],
                "expected_sources": ["ERP"],
                "answer_requirements": [],
            },
            "sources": ["ERP"],
            "tool_calls": [
                ToolCallTrace(tool="ERPTool", status="success", source="ERP")
            ],
            "reasoning": ["Consulta ERP de pedidos pendientes"],
            "attempts": 0,
        }
    )

    assert state["status"] == "completed"
    assert state["validation_decision"] == "finish"


def test_validator_replans_when_required_source_is_missing() -> None:
    validator = ValidatorNode()

    state = validator(
        {
            "plan": {
                "intent": "erp_production",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "ERPTool",
                        "action": "get_pending_orders_by_customer",
                        "args": {"customer_id": "ALFKI"},
                        "required": True,
                    }
                ],
                "expected_sources": ["ERP", "Produccion"],
                "answer_requirements": [],
            },
            "sources": ["ERP"],
            "tool_calls": [
                ToolCallTrace(tool="ERPTool", status="success", source="ERP")
            ],
            "reasoning": ["Consulta ERP de pedidos pendientes"],
            "attempts": 0,
        }
    )

    assert state["status"] == "partial_answer"
    assert state["validation_decision"] == "replan"
    assert state["attempts"] == 1
    assert state["replan_history"] == [
        {
            "attempt": 1,
            "decision": "replan",
            "status": "partial_answer",
            "failure_reason": "Faltan fuentes obligatorias: Produccion.",
            "max_replans": 2,
        }
    ]


def test_validator_fails_rag_when_context_is_insufficient() -> None:
    validator = ValidatorNode()

    state = validator(
        {
            "plan": {
                "intent": "rag",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "DocumentRAGTool",
                        "action": "query",
                        "args": {"query": "contrato"},
                        "required": True,
                    }
                ],
                "expected_sources": ["Documentos"],
                "answer_requirements": [],
            },
            "sources": ["Documentos"],
            "tool_calls": [
                ToolCallTrace(tool="DocumentRAGTool", status="success", source="Documentos")
            ],
            "reasoning": ["Consulta RAG documental con chunks recuperados"],
            "data": {
                "rag": {
                    "answer": "No hay contexto documental suficiente para responder sin inventar.",
                    "status": "insufficient_context",
                    "chunks": [],
                }
            },
            "attempts": 0,
        }
    )

    assert state["status"] == "insufficient_context"
    assert state["validation_decision"] == "fail"


def test_validator_finishes_clarification_without_replanning() -> None:
    validator = ValidatorNode()

    state = validator(
        {
            "plan": {
                "intent": "clarification",
                "steps": [],
                "expected_sources": [],
                "answer_requirements": ["Pedir el cliente concreto."],
            },
            "sources": [],
            "tool_calls": [],
            "reasoning": [],
            "attempts": 0,
        }
    )

    assert state["status"] == "needs_clarification"
    assert state["validation_decision"] == "fail"
    assert "Falta informacion" in state["failure_reason"]
    assert state.get("attempts") == 0


def test_validator_fails_mixed_plan_when_document_context_is_insufficient() -> None:
    validator = ValidatorNode()

    state = validator(
        {
            "plan": {
                "intent": "mixed",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "ERPTool",
                        "action": "get_orders_by_month",
                        "args": {"year": 2026, "month": 5},
                        "required": True,
                    },
                    {
                        "step_id": 2,
                        "tool": "ProductionAPITool",
                        "action": "get_status_for_erp_orders",
                        "args": {},
                        "required": True,
                    },
                    {
                        "step_id": 3,
                        "tool": "DocumentRAGTool",
                        "action": "query",
                        "args": {"query": "penalizaciones", "top_k": 5},
                        "required": True,
                    },
                ],
                "expected_sources": ["ERP", "Produccion", "Documentos"],
                "answer_requirements": [],
            },
            "sources": ["ERP", "Produccion", "Documentos"],
            "tool_calls": [
                ToolCallTrace(tool="ERPTool", status="success", source="ERP"),
                ToolCallTrace(
                    tool="ProductionAPITool",
                    status="success",
                    source="Produccion",
                ),
                ToolCallTrace(
                    tool="DocumentRAGTool",
                    status="success",
                    source="Documentos",
                ),
            ],
            "reasoning": [
                "Consulta ERP de pedidos por mes",
                "Consulta API de produccion para pedido 10248",
                "Consulta RAG documental con chunks recuperados",
            ],
            "data": {
                "rag": {
                    "answer": "No hay contexto documental suficiente para responder sin inventar.",
                    "status": "insufficient_context",
                    "chunks": [],
                }
            },
            "attempts": 0,
        }
    )

    assert state["status"] == "insufficient_context"
    assert state["validation_decision"] == "fail"


def test_validator_finishes_rag_when_document_context_exists() -> None:
    validator = ValidatorNode()

    state = validator(
        {
            "plan": {
                "intent": "rag",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "DocumentRAGTool",
                        "action": "query",
                        "args": {"query": "contrato"},
                        "required": True,
                    }
                ],
                "expected_sources": ["Documentos"],
                "answer_requirements": [],
            },
            "sources": ["Documentos"],
            "tool_calls": [
                ToolCallTrace(tool="DocumentRAGTool", status="success", source="Documentos")
            ],
            "reasoning": ["Consulta RAG documental con chunks recuperados"],
            "data": {
                "rag": {
                    "answer": "Respuesta basada en chunks.",
                    "status": "completed",
                    "chunks": [{"chunk_id": "chunk-1"}],
                }
            },
            "attempts": 0,
        }
    )

    assert state["status"] == "completed"
    assert state["validation_decision"] == "finish"


def test_validator_replans_when_visible_reasoning_is_missing() -> None:
    validator = ValidatorNode()

    state = validator(
        {
            "plan": {
                "intent": "erp",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "ERPTool",
                        "action": "get_pending_orders_by_customer",
                        "args": {"customer_id": "ALFKI"},
                        "required": True,
                    }
                ],
                "expected_sources": ["ERP"],
                "answer_requirements": [],
            },
            "sources": ["ERP"],
            "tool_calls": [
                ToolCallTrace(tool="ERPTool", status="success", source="ERP")
            ],
            "reasoning": [],
            "attempts": 0,
        }
    )

    assert state["status"] == "failed"
    assert state["validation_decision"] == "replan"
    assert state["attempts"] == 1
    assert state["replan_history"][0]["failure_reason"] == (
        "El plan tenia pasos pero no se registraron pasos visibles de trazabilidad."
    )


def test_validator_preserves_replan_history_when_max_replans_is_reached() -> None:
    validator = ValidatorNode()

    state = validator(
        {
            "plan": {
                "intent": "erp_production",
                "steps": [
                    {
                        "step_id": 1,
                        "tool": "ERPTool",
                        "action": "get_pending_orders_by_customer",
                        "args": {"customer_id": "ALFKI"},
                        "required": True,
                    }
                ],
                "expected_sources": ["ERP", "Produccion"],
                "answer_requirements": [],
            },
            "sources": ["ERP"],
            "tool_calls": [
                ToolCallTrace(tool="ERPTool", status="success", source="ERP")
            ],
            "reasoning": ["Consulta ERP de pedidos pendientes"],
            "attempts": 2,
            "replan_history": [
                {
                    "attempt": 1,
                    "decision": "replan",
                    "status": "partial_answer",
                    "failure_reason": "Faltan fuentes obligatorias: Produccion.",
                    "max_replans": 2,
                }
            ],
        }
    )

    assert state["status"] == "partial_answer"
    assert state["validation_decision"] == "fail"
    assert state["replan_history"] == [
        {
            "attempt": 1,
            "decision": "replan",
            "status": "partial_answer",
            "failure_reason": "Faltan fuentes obligatorias: Produccion.",
            "max_replans": 2,
        }
    ]
