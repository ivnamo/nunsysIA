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


def test_planner_marks_pending_orders_without_customer_as_clarification() -> None:
    planner = PlannerAgent()

    state = planner({"question": "Que pedidos pendientes hay?", "attempts": 0})

    assert state["intent"] == "clarification"
    assert state["plan"]["steps"] == []
    assert "cliente concreto" in state["plan"]["answer_requirements"][0]


def test_planner_does_not_default_llm_pending_order_plan_to_alfki() -> None:
    chat_model = _FakeChatModel(
        """
        {
          "intent": "erp",
          "steps": [
            {
              "step_id": 1,
              "tool": "ERPTool",
              "action": "get_pending_orders_by_customer",
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

    state = planner({"question": "Que pedidos pendientes hay?", "attempts": 0})

    assert chat_model.calls == 1
    assert state["intent"] == "clarification"
    assert state["plan"]["steps"] == []
    assert "ALFKI" not in str(state["plan"])


def test_planner_normalizes_llm_clarification_for_pending_orders() -> None:
    chat_model = _FakeChatModel(
        """
        {
          "intent": "clarification",
          "steps": [],
          "expected_sources": [],
          "answer_requirements": []
        }
        """
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner({"question": "Que pedidos pendientes hay?", "attempts": 0})

    assert chat_model.calls == 1
    assert state["intent"] == "clarification"
    assert state["plan"]["steps"] == []
    assert "cliente concreto" in state["plan"]["answer_requirements"][0]


def test_planner_creates_blocked_orders_plan() -> None:
    planner = PlannerAgent()

    state = planner({"question": "Que pedidos estan bloqueados?", "attempts": 0})

    assert state["intent"] == "erp_production"
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "list_orders",
        "get_customers_for_production_orders",
    ]


def test_planner_routes_problematic_production_orders_to_blocked_and_delayed() -> None:
    planner = PlannerAgent()

    state = planner(
        {
            "question": "Que pedidos tengo parados o con problemas de produccion?",
            "attempts": 0,
        }
    )

    assert state["intent"] == "erp_production"
    assert state["plan"]["expected_sources"] == ["Produccion", "ERP"]
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "list_orders",
        "list_orders",
        "get_customers_for_production_orders",
    ]
    assert state["plan"]["steps"][0]["args"] == {"status": "blocked"}
    assert state["plan"]["steps"][1]["args"] == {"status": "delayed"}


def test_planner_routes_cross_blocked_customers_to_safe_query_dsl() -> None:
    planner = PlannerAgent()

    state = planner(
        {
            "question": "Cruza produccion con ERP y dime clientes afectados por bloqueos.",
            "attempts": 0,
        }
    )

    assert state["intent"] == "erp_production"
    assert state["plan"]["expected_sources"] == ["Produccion", "ERP"]
    assert [step["tool"] for step in state["plan"]["steps"]] == [
        "ProductionQueryTool",
        "ERPQueryTool",
    ]
    assert state["plan"]["steps"][0]["args"]["spec"]["filters"] == [
        {
            "field": "production_status",
            "operator": "eq",
            "value": "blocked",
        }
    ]
    assert state["plan"]["steps"][1]["args"]["join_from"] == "production_orders"
    assert state["plan"]["steps"][1]["args"]["spec"]["select"] == [
        "order_id",
        "customer_id",
        "customer_name",
    ]


def test_planner_routes_lowercase_customer_with_operational_risk() -> None:
    planner = PlannerAgent()

    state = planner(
        {
            "question": "que tiene pendiente alfki y que riesgo operativo tiene?",
            "attempts": 0,
        }
    )

    assert state["intent"] == "erp_production"
    assert state["plan"]["expected_sources"] == ["ERP", "Produccion"]
    assert state["plan"]["steps"][0]["args"] == {"customer_id": "ALFKI"}
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "get_pending_orders_by_customer",
        "get_status_for_erp_orders",
    ]


def test_planner_routes_explicit_order_id_status_query() -> None:
    planner = PlannerAgent()

    state = planner(
        {"question": "en que estado esta el pedido 10252?", "attempts": 0}
    )

    assert state["intent"] == "erp_production"
    assert state["plan"]["expected_sources"] == ["Produccion", "ERP"]
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "get_status_for_order_ids",
        "get_customers_for_production_orders",
    ]
    assert state["plan"]["steps"][0]["args"] == {"order_ids": [10252]}


def test_planner_routes_bare_explicit_order_id_query() -> None:
    planner = PlannerAgent()

    state = planner({"question": "pedido 10252", "attempts": 0})

    assert state["intent"] == "erp_production"
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "get_status_for_order_ids",
        "get_customers_for_production_orders",
    ]
    assert state["plan"]["steps"][0]["args"] == {"order_ids": [10252]}


def test_planner_prefers_rules_for_bare_order_id_even_with_llm() -> None:
    chat_model = _FakeChatModel(
        """
        {
          "intent": "clarification",
          "steps": [],
          "expected_sources": [],
          "answer_requirements": ["Pedir mas contexto."]
        }
        """
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner({"question": "pedido 10252", "attempts": 0})

    assert chat_model.calls == 0
    assert state["intent"] == "erp_production"
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "get_status_for_order_ids",
        "get_customers_for_production_orders",
    ]


def test_planner_prefers_rules_for_problematic_production_even_with_llm() -> None:
    chat_model = _FakeChatModel(
        '{"intent": "unsupported", "steps": [], "expected_sources": []}'
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner(
        {
            "question": "Que pedidos tengo parados o con problemas de produccion?",
            "attempts": 0,
        }
    )

    assert chat_model.calls == 0
    assert [step["args"] for step in state["plan"]["steps"][:2]] == [
        {"status": "blocked"},
        {"status": "delayed"},
    ]


def test_planner_prefers_rules_for_customer_operational_risk_even_with_llm() -> None:
    chat_model = _FakeChatModel(
        '{"intent": "clarification", "steps": [], "expected_sources": []}'
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner(
        {
            "question": "que tiene pendiente alfki y que riesgo operativo tiene?",
            "attempts": 0,
        }
    )

    assert chat_model.calls == 0
    assert state["intent"] == "erp_production"
    assert state["plan"]["steps"][0]["args"] == {"customer_id": "ALFKI"}


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


def test_planner_routes_potential_order_penalty_question_as_mixed_without_llm() -> None:
    chat_model = _FakeChatModel(
        """
        {
          "intent": "rag",
          "steps": [
            {
              "step_id": 1,
              "tool": "DocumentRAGTool",
              "action": "query",
              "args": {"query": "Dame los pedidos que puedan generar penalizacion y dime por que.", "top_k": 5},
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
            "question": "Dame los pedidos que puedan generar penalizacion y dime por que.",
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
    assert "falta material" in state["plan"]["steps"][2]["args"]["query"]


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


def test_planner_uses_memory_and_order_ids_for_blocked_follow_up() -> None:
    planner = PlannerAgent(
        chat_model=_FakeChatModel('{"intent": "unsupported", "steps": [], "expected_sources": []}')
    )

    state = planner(
        {
            "question": "Y cuales de esos pedidos estan bloqueados?",
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
    assert state["plan"]["expected_sources"] == ["Memoria", "Produccion", "ERP"]
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "recall",
        "get_status_for_order_ids",
        "get_customers_for_production_orders",
    ]
    assert state["plan"]["steps"][1]["args"] == {
        "order_ids": [10248, 10252],
        "status": "blocked",
    }


def test_planner_uses_memory_and_amounts_for_economic_impact_follow_up() -> None:
    planner = PlannerAgent(
        chat_model=_FakeChatModel('{"intent": "unsupported", "steps": [], "expected_sources": []}')
    )

    state = planner(
        {
            "question": "Cual es el impacto economico de esos?",
            "attempts": 0,
            "conversation_history": [
                {
                    "question": "Y cuales de esos pedidos estan bloqueados?",
                    "answer": "El pedido 10252 esta bloqueado por Falta de material.",
                    "facts": {"customer_id": "ALFKI", "order_ids": [10252]},
                }
            ],
        }
    )

    assert state["intent"] == "erp"
    assert state["plan"]["expected_sources"] == ["Memoria", "ERP"]
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "recall",
        "calculate_order_amount",
    ]
    assert state["plan"]["steps"][1]["args"] == {"order_ids": [10252]}


def test_planner_marks_isolated_contextual_follow_up_as_clarification_before_llm() -> None:
    chat_model = _FakeChatModel(
        """
        {
          "intent": "erp_production",
          "steps": [
            {
              "step_id": 1,
              "tool": "ProductionAPITool",
              "action": "get_status_for_order_ids",
              "args": {"order_ids": [], "status": "blocked"},
              "required": true
            }
          ],
          "expected_sources": ["Produccion"],
          "answer_requirements": []
        }
        """
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner({"question": "Y en que estado estan?", "attempts": 0})

    assert chat_model.calls == 0
    assert state["intent"] == "clarification"
    assert state["plan"]["steps"] == []
    assert "contexto conversacional previo" in state["plan"]["answer_requirements"][0]


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


def test_planner_normalizes_allowed_llm_query_dsl_plan() -> None:
    chat_model = _FakeChatModel(
        """
        {
          "intent": "erp_production",
          "steps": [
            {
              "step_id": 1,
              "tool": "ProductionQueryTool",
              "action": "query_orders",
              "args": {
                "spec": {
                  "entity": "production_orders",
                  "filters": [
                    {
                      "field": "production_status",
                      "operator": "eq",
                      "value": "BLOCKED"
                    }
                  ],
                  "select": ["order_id", "production_status", "blocked_reason"],
                  "limit": 50
                }
              },
              "required": true
            },
            {
              "step_id": 2,
              "tool": "ERPQueryTool",
              "action": "query_orders",
              "args": {
                "spec": {
                  "entity": "orders",
                  "select": ["order_id", "customer_id", "customer_name"],
                  "limit": 50
                },
                "join_from": "production_orders"
              },
              "required": true
            }
          ],
          "expected_sources": ["Produccion", "ERP"],
          "answer_requirements": ["Cruzar por order_id."]
        }
        """
    )
    planner = PlannerAgent(chat_model=chat_model)

    state = planner(
        {
            "question": "Haz una consulta operativa segura.",
            "attempts": 0,
        }
    )

    assert state.get("fallbacks") == []
    assert state["plan"]["steps"][0]["args"]["spec"]["filters"][0]["value"] == "blocked"
    assert state["plan"]["steps"][0]["args"]["spec"]["limit"] == 50
    assert state["plan"]["steps"][1]["args"]["join_from"] == "production_orders"


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
