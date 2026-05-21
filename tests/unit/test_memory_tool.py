from app.schemas.query import QueryResponse
from app.tools.memory_tool import (
    ConversationMemoryStore,
    MemoryRecallInput,
    MemoryTool,
)


def test_conversation_memory_store_keeps_last_five_turns() -> None:
    store = ConversationMemoryStore()

    for index in range(6):
        store.remember(
            conversation_id="demo-001",
            question=f"Pregunta {index} ALFKI",
            response=QueryResponse(
                answer=f"Respuesta {index}",
                sources=["ERP"],
                status="completed",
                data={"erp_order_ids": [10248 + index]},
            ),
        )

    history = store.history("demo-001")

    assert len(history) == 5
    assert history[0]["question"] == "Pregunta 1 ALFKI"
    assert history[-1]["facts"]["order_ids"] == [10253]


def test_conversation_memory_store_is_isolated_by_conversation_id() -> None:
    store = ConversationMemoryStore()
    store.remember(
        conversation_id="demo-001",
        question="Que pedidos pendientes tiene ALFKI?",
        response=QueryResponse(
            answer="El cliente ALFKI tiene 2 pedidos pendientes.",
            sources=["ERP"],
            status="completed",
            data={"erp_order_ids": [10248, 10252]},
        ),
    )

    assert store.history("demo-002") == []
    assert store.history(None) == []


def test_memory_tool_returns_public_history_and_facts() -> None:
    tool = MemoryTool()

    result = tool.recall(
        MemoryRecallInput(
            query="Y en que estado estan?",
            conversation_history=[
                {
                    "question": "Que pedidos pendientes tiene ALFKI?",
                    "answer": "El cliente ALFKI tiene 2 pedidos pendientes.",
                    "status": "completed",
                    "sources": ["ERP"],
                    "facts": {"customer_id": "ALFKI", "order_ids": [10248, 10252]},
                }
            ],
        )
    )

    assert result.tool_call.tool == "MemoryTool"
    assert result.tool_call.source == "Memoria"
    assert result.tool_call.status == "success"
    assert result.data["status"] == "found"
    assert result.data["facts"] == {
        "customer_id": "ALFKI",
        "order_ids": [10248, 10252],
    }
