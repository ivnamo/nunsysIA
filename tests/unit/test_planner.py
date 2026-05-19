from app.agents.planner import PlannerAgent


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


def test_planner_creates_blocked_orders_plan() -> None:
    planner = PlannerAgent()

    state = planner({"question": "Que pedidos estan bloqueados?", "attempts": 0})

    assert state["intent"] == "erp_production"
    assert [step["action"] for step in state["plan"]["steps"]] == [
        "list_orders",
        "get_customers_for_production_orders",
    ]


def test_planner_marks_documental_query_as_rag_without_tool_steps() -> None:
    planner = PlannerAgent()

    state = planner({"question": "Resume el PDF del contrato marco", "attempts": 0})

    assert state["intent"] == "rag"
    assert state["plan"]["steps"] == []
    assert state["plan"]["expected_sources"] == ["Documentos"]


def test_planner_marks_out_of_scope_query_as_unsupported() -> None:
    planner = PlannerAgent()

    state = planner({"question": "Que tiempo hace hoy?", "attempts": 0})

    assert state["intent"] == "unsupported"
    assert state["plan"]["steps"] == []
