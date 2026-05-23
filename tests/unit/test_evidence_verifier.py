from app.agents.deepagents_policy import tool_policy
from app.agents.evidence_verifier import verify_response
from app.core.tracing import ToolCallTrace
from app.schemas.query import QueryResponse


def test_evidence_verifier_rejects_missing_required_tool_calls() -> None:
    policy = tool_policy(
        "Que pedidos pendientes tiene ALFKI y en que estado de produccion estan?",
        [],
    )
    response = QueryResponse(
        answer="ALFKI tiene pedidos pendientes.",
        sources=["ERP"],
        reasoning=["Consulta ERP"],
        tool_calls=[
            ToolCallTrace(
                tool="ERPTool",
                action="get_pending_orders_by_customer",
                args={"customer_id": "ALFKI"},
                status="success",
                source="ERP",
            )
        ],
        status="completed",
    )

    result = verify_response(response, policy=policy, data={"erp_orders": []})

    assert not result.passed
    assert "falta evidencia obligatoria de Produccion" in result.issues


def test_evidence_verifier_rejects_rag_without_citations() -> None:
    policy = tool_policy("Que dice el documento sobre plazos de entrega?", [])
    response = QueryResponse(
        answer="El documento habla de plazos.",
        sources=["Documentos"],
        reasoning=["Consulta RAG"],
        tool_calls=[
            ToolCallTrace(
                tool="DocumentRAGTool",
                action="query",
                args={"query": "plazos"},
                status="success",
                source="Documentos",
            )
        ],
        status="completed",
    )

    result = verify_response(
        response,
        policy=policy,
        data={"rag": {"status": "completed", "chunks": []}},
    )

    assert not result.passed
    assert "RAG no aporta citas documentales auditables" in result.issues


def test_evidence_verifier_accepts_grounded_rag_response() -> None:
    policy = tool_policy("Que dice el documento sobre plazos de entrega?", [])
    response = QueryResponse(
        answer="El contrato fija 5 dias laborables.",
        sources=["Documentos"],
        reasoning=["Consulta RAG"],
        tool_calls=[
            ToolCallTrace(
                tool="DocumentRAGTool",
                action="query",
                args={"query": "plazos"},
                status="success",
                source="Documentos",
            )
        ],
        status="completed",
    )

    result = verify_response(
        response,
        policy=policy,
        data={
            "rag": {
                "status": "completed",
                "chunks": [
                    {
                        "metadata": {
                            "filename": "contrato.pdf",
                            "page": 2,
                            "chunk_id": "doc_p2_c1",
                        }
                    }
                ],
            }
        },
    )

    assert result.passed

