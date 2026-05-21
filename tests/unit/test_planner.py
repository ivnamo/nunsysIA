import time

from app.agents.planner import PlannerAgent


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
        return _FakeMessage("{}")


def test_planner_creates_erp_production_plan_for_pending_orders() -> None:
    planner = PlannerAgent()

    state = planner(
        {
            "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
            "attempts": 0,
        }
    )

    assert state["intent"] == "erp_production"
    assert state["plan"]["expected_sources"] == ["ERP", "Produccion"]
    assert [step["tool"] for step in state["plan"]["steps"]] == [
        "ERPTool",
        "ProductionAPITool",
    ]
    assert state["plan"]["steps"][0]["args"] == {"customer_id": "ALFKI"}
    assert state["fallbacks"] == [
        "FALLBACK_PLANNER_RULE_BASED: LLM planner no configurado; plan creado por reglas."
    ]


def test_planner_creates_blocked_orders_plan() -> None:
    planner = PlannerAgent()

    state = planner({"question": "Que pedidos estan bloqueados?", "attempts": 0})

    assert state["intent"] == "erp_production"
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "list_orders",
        "get_customers_for_production_orders",
    ]


def test_planner_marks_documental_query_as_rag_with_document_tool_step() -> None:
    planner = PlannerAgent()

    state = planner({"question": "Resume el PDF del contrato marco", "attempts": 0})

    assert state["intent"] == "rag"
    assert state["plan"]["steps"][0]["tool"] == "DocumentRAGTool"
    assert state["plan"]["steps"][0]["action"] == "query"
    assert state["plan"]["expected_sources"] == ["Documentos"]


def test_planner_routes_order_penalty_question_as_mixed_without_llm() -> None:
    chat_model = _FakeChatModel(
        """
        {
          "intent": "rag",
          "steps": [
            {
              "step_id": 1,
              "tool": "DocumentRAGTool",
              "action": "query",
              "args": {"query": "penalizaciones", "top_k": 5},
              "required": true
            }
          ],
          "expected_sources": ["Documentos"],
          "answer_requirements": []
        }
        """
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner(
        {
            "question": "en funcion de los pedidos y su estado dime que penalizaciones vamos a tener en cada uno",
            "attempts": 0,
        }
    )

    assert chat_model.calls == 0
    assert state["intent"] == "mixed"
    assert state["plan"]["expected_sources"] == ["ERP", "Produccion", "Documentos"]
    assert [step["tool"] for step in state["plan"]["steps"]] == [
        "ERPTool",
        "ProductionAPITool",
        "DocumentRAGTool",
    ]
    assert state["plan"]["steps"][0]["action"] == "get_orders_by_month"
    assert state["plan"]["steps"][1]["action"] == "get_status_for_erp_orders"
    assert state["plan"]["steps"][2]["action"] == "query"


def test_planner_marks_out_of_scope_query_as_unsupported() -> None:
    planner = PlannerAgent()

    state = planner({"question": "Que tiempo hace hoy?", "attempts": 0})

    assert state["intent"] == "unsupported"
    assert state["plan"]["steps"] == []


def test_planner_uses_memory_for_contextual_follow_up() -> None:
    planner = PlannerAgent()

    state = planner(
        {
            "question": "Y en que estado estan?",
            "attempts": 0,
            "conversation_history": [
                {
                    "question": "Que pedidos pendientes tiene el cliente ALFKI?",
                    "answer": "El cliente ALFKI tiene 2 pedidos pendientes: 10248, 10252.",
                    "facts": {"customer_id": "ALFKI", "order_ids": [10248, 10252]},
                }
            ],
        }
    )

    assert state["intent"] == "erp_production"
    assert state["plan"]["expected_sources"] == ["Memoria", "ERP", "Produccion"]
    assert [step["tool"] for step in state["plan"]["steps"]] == [
        "MemoryTool",
        "ERPTool",
        "ProductionAPITool",
    ]
    assert state["plan"]["steps"][1]["args"] == {"customer_id": "ALFKI"}


def test_planner_uses_llm_plan_when_it_matches_allowed_contract() -> None:
    chat_model = _FakeChatModel(
        """
        {
          "intent": "erp_production",
          "steps": [
            {
              "step_id": 10,
              "tool": "ProductionAPITool",
              "action": "list_orders",
              "args": {"status": "delayed"},
              "required": true
            },
            {
              "step_id": 20,
              "tool": "ERPTool",
              "action": "get_customers_for_production_orders",
              "args": {"unsafe": "ignored"},
              "required": true
            }
          ],
          "expected_sources": ["Produccion", "ERP"],
          "answer_requirements": ["Cruzar retrasos de produccion con clientes ERP."]
        }
        """
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner(
        {
            "question": "Que clientes tienen pedidos retrasados por problemas de produccion?",
            "attempts": 0,
        }
    )

    assert chat_model.calls == 1
    assert state["intent"] == "erp_production"
    assert state.get("fallbacks") == []
    assert state["plan"]["expected_sources"] == ["Produccion", "ERP"]
    assert [step["step_id"] for step in state["plan"]["steps"]] == [1, 2]
    assert state["plan"]["steps"][0]["args"] == {"status": "delayed"}
    assert state["plan"]["steps"][1]["args"] == {}


def test_planner_accepts_markdown_wrapped_llm_json() -> None:
    chat_model = _FakeChatModel(
        """```json
        {
          "intent": "rag",
          "steps": [
            {
              "step_id": 1,
              "tool": "DocumentRAGTool",
              "action": "query",
              "args": {"query": "penalizaciones", "top_k": 99},
              "required": true
            }
          ],
          "expected_sources": ["Documentos"],
          "answer_requirements": ["Usar solo chunks recuperados."]
        }
        ```"""
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner({"question": "Hay alguna penalizacion por retrasos?", "attempts": 0})

    assert state["intent"] == "rag"
    assert state["plan"]["steps"][0]["args"] == {
        "query": "penalizaciones",
        "top_k": 10,
    }


def test_planner_falls_back_to_rules_when_llm_plan_uses_disallowed_action() -> None:
    chat_model = _FakeChatModel(
        """
        {
          "intent": "erp",
          "steps": [
            {
              "step_id": 1,
              "tool": "ERPTool",
              "action": "drop_database",
              "args": {},
              "required": true
            }
          ],
          "expected_sources": ["ERP"],
          "answer_requirements": []
        }
        """
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner(
        {
            "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
            "attempts": 0,
        }
    )

    assert state["intent"] == "erp_production"
    assert [step["tool"] for step in state["plan"]["steps"]] == [
        "ERPTool",
        "ProductionAPITool",
    ]
    assert len(state["fallbacks"]) == 1
    assert state["fallbacks"][0].startswith(
        "FALLBACK_PLANNER_RULE_BASED: LLM planner fallo"
    )
    assert "plan no valido" in state["fallbacks"][0]


def test_planner_falls_back_to_rules_when_llm_times_out() -> None:
    planner = PlannerAgent(
        chat_model=_SlowChatModel(),
        llm_timeout_seconds=0.01,
    )

    state = planner(
        {
            "question": "Que pedidos estan bloqueados?",
            "attempts": 0,
        }
    )

    assert state["intent"] == "erp_production"
    assert state["plan"]["steps"][0]["tool"] == "ProductionAPITool"
    assert state["plan"]["steps"][0]["args"] == {"status": "blocked"}
    assert len(state["fallbacks"]) == 1
    assert state["fallbacks"][0].startswith(
        "FALLBACK_PLANNER_RULE_BASED: LLM planner fallo"
    )
    assert "TimeoutError" in state["fallbacks"][0]
