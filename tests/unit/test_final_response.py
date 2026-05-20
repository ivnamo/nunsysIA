import time

from app.agents.final_response import FinalResponseBuilder


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChatModel:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0

    def invoke(self, input: object, **kwargs: object) -> _FakeMessage:
        self.calls += 1
        return _FakeMessage(self.content)


class _SlowChatModel:
    def invoke(self, input: object, **kwargs: object) -> _FakeMessage:
        time.sleep(0.2)
        return _FakeMessage('{"answer": "Respuesta tardia"}')


class _ExplodingChatModel:
    def invoke(self, input: object, **kwargs: object) -> _FakeMessage:
        raise Exception("provider unavailable")


def test_final_response_uses_grounded_llm_answer_when_available() -> None:
    chat_model = _FakeChatModel(
        '{"answer": "El cliente ALFKI tiene 2 pedidos pendientes. '
        'El pedido 10248 esta en curso en produccion y el pedido 10252 '
        'esta bloqueado por Falta de material."}'
    )
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(_erp_production_state())

    assert chat_model.calls == 1
    assert state["response"].answer.startswith("El cliente ALFKI tiene 2 pedidos")
    assert "ERP pending" not in state["response"].answer
    assert state["response"].status == "completed"
    assert state["response"].fallbacks == []


def test_final_response_falls_back_when_llm_adds_unsupported_number() -> None:
    chat_model = _FakeChatModel(
        '{"answer": "El cliente ALFKI tiene 3 pedidos pendientes."}'
    )
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(_erp_production_state())

    assert state["response"].answer == (
        "Pedidos del cliente ALFKI: 10248: ERP pendiente, produccion en curso; "
        "10252: ERP pendiente, produccion bloqueado (Falta de material)."
    )
    assert state["response"].fallbacks == [
        "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final no paso validacion de evidencias; respuesta construida por reglas."
    ]


def test_final_response_falls_back_when_llm_times_out() -> None:
    builder = FinalResponseBuilder(
        chat_model=_SlowChatModel(),
        llm_timeout_seconds=0.01,
    )

    state = builder(_erp_production_state())

    assert "Pedidos del cliente ALFKI" in state["response"].answer
    assert len(state["response"].fallbacks) == 1
    assert state["response"].fallbacks[0].startswith(
        "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final fallo o no devolvio JSON valido"
    )
    assert "TimeoutError" in state["response"].fallbacks[0]


def test_final_response_falls_back_when_llm_provider_fails() -> None:
    builder = FinalResponseBuilder(chat_model=_ExplodingChatModel())

    state = builder(_erp_production_state())

    assert "Pedidos del cliente ALFKI" in state["response"].answer
    assert state["response"].status == "completed"
    assert len(state["response"].fallbacks) == 1
    assert state["response"].fallbacks[0].startswith(
        "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final fallo"
    )
    assert "Exception" in state["response"].fallbacks[0]


def test_final_response_marks_fallback_when_llm_is_not_configured() -> None:
    builder = FinalResponseBuilder()

    state = builder(_erp_production_state())

    assert "Pedidos del cliente ALFKI" in state["response"].answer
    assert state["response"].fallbacks == [
        "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final no configurado; respuesta construida por reglas."
    ]


def test_final_response_does_not_call_llm_for_insufficient_context() -> None:
    chat_model = _FakeChatModel('{"answer": "Invento una respuesta"}')
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(
        {
            "question": "Que dice el documento?",
            "plan": {
                "intent": "rag",
                "steps": [],
                "expected_sources": ["Documentos"],
                "answer_requirements": [],
            },
            "status": "insufficient_context",
            "data": {
                "rag": {
                    "answer": "No hay contexto documental suficiente para responder sin inventar.",
                    "status": "insufficient_context",
                    "chunks": [],
                }
            },
            "sources": [],
            "reasoning": [],
            "tool_calls": [],
        }
    )

    assert chat_model.calls == 0
    assert state["response"].answer == (
        "No hay contexto documental suficiente para responder sin inventar."
    )


def _erp_production_state() -> dict:
    return {
        "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
        "plan": {
            "intent": "erp_production",
            "steps": [],
            "expected_sources": ["ERP", "Produccion"],
            "answer_requirements": [],
        },
        "status": "completed",
        "data": {
            "erp_orders": [
                {
                    "order_id": 10248,
                    "customer_id": "ALFKI",
                    "erp_status": "pending",
                },
                {
                    "order_id": 10252,
                    "customer_id": "ALFKI",
                    "erp_status": "pending",
                },
            ],
            "production_by_order": {
                10248: {
                    "order_id": 10248,
                    "production_status": "in_progress",
                    "blocked_reason": None,
                    "delay_reason": None,
                },
                10252: {
                    "order_id": 10252,
                    "production_status": "blocked",
                    "blocked_reason": "Falta de material",
                    "delay_reason": None,
                },
            },
        },
        "sources": ["ERP", "Produccion"],
        "reasoning": [
            "Consulta ERP de pedidos pendientes",
            "Consulta API de produccion para pedido 10248",
            "Consulta API de produccion para pedido 10252",
        ],
        "tool_calls": [],
    }
