from app.services.response_normalizer import ResponseNormalizer
from app.schemas.query import AgentMode, QueryResponse
from app.services.trace_service import TraceService


def test_response_normalizer_preserves_query_response_shape() -> None:
    response = ResponseNormalizer().normalize(
        QueryResponse(
            answer="Respuesta",
            sources=["ERP"],
            reasoning=["Consulta ERP"],
        ),
        AgentMode.DEEPAGENT,
    )

    assert isinstance(response.answer, str)
    assert isinstance(response.sources, list)
    assert isinstance(response.reasoning, list)
    assert response.metadata == {
        "agent_mode": "deepagent",
        "agent_framework": "LangChain DeepAgents",
    }


def test_response_normalizer_infers_sources_and_reasoning_from_tool_calls() -> None:
    response = ResponseNormalizer().normalize(
        {
            "answer": "Pedidos consultados",
            "tool_calls": [
                {
                    "tool": "ERPTool",
                    "action": "query_erp_orders",
                    "args": {},
                    "status": "success",
                    "source": "ERP",
                },
                {
                    "tool": "ProductionAPITool",
                    "action": "query_production_status",
                    "args": {},
                    "status": "success",
                    "source": "Produccion",
                },
            ],
        },
        AgentMode.DEEPAGENT,
    )

    assert response.sources == ["ERP", "Produccion"]
    assert response.reasoning == [
        "Consulta ERP para query_erp_orders",
        "Consulta API de produccion para query_production_status",
    ]


def test_response_normalizer_does_not_reuse_previous_trace_events() -> None:
    normalizer = ResponseNormalizer(trace_service=TraceService())

    first = normalizer.normalize(
        {
            "answer": "Pedidos consultados",
            "tool_calls": [
                {
                    "tool": "ERPTool",
                    "action": "query_erp_orders",
                    "args": {},
                    "status": "success",
                    "source": "ERP",
                }
            ],
        },
        AgentMode.DEEPAGENT,
    )
    second = normalizer.normalize(
        QueryResponse(
            answer="Necesito que indiques el cliente.",
            sources=[],
            reasoning=[],
            status="needs_clarification",
        ),
        AgentMode.DEEPAGENT,
    )

    assert first.sources == ["ERP"]
    assert second.sources == []
    assert second.reasoning == []


def test_response_normalizer_marks_experimental_modes() -> None:
    response = ResponseNormalizer().normalize(
        QueryResponse(answer="Legacy", sources=["ERP"], reasoning=["Consulta"]),
        AgentMode.LEGACY_LANGGRAPH,
    )

    assert response.metadata["agent_mode"] == "legacy_langgraph"
    assert response.metadata["agent_framework"] == "LangGraph legacy"
    assert response.metadata["experimental"] is True
