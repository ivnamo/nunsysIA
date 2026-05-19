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
            "attempts": 0,
        }
    )

    assert state["status"] == "partial_answer"
    assert state["validation_decision"] == "replan"
    assert state["attempts"] == 1


def test_validator_fails_rag_until_document_pipeline_exists() -> None:
    validator = ValidatorNode()

    state = validator(
        {
            "plan": {
                "intent": "rag",
                "steps": [],
                "expected_sources": ["Documentos"],
                "answer_requirements": [],
            },
            "sources": [],
            "tool_calls": [],
            "attempts": 0,
        }
    )

    assert state["status"] == "insufficient_context"
    assert state["validation_decision"] == "fail"
