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
            ),
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
            ),
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


def test_evidence_verifier_rejects_prompt_echo() -> None:
    policy = tool_policy("Dame un resumen del estado de los pedidos de este mes", [])
    response = QueryResponse(
        answer="Pregunta: Dame un resumen\nconversation_id:\nUsa solo las tools",
        sources=["ERP", "Produccion"],
        reasoning=["Consulta ERP", "Consulta produccion"],
        tool_calls=[
            ToolCallTrace(
                tool="ERPTool",
                action="get_orders_by_month",
                args={"year": 2026, "month": 5},
                status="success",
                source="ERP",
            ),
            ToolCallTrace(
                tool="ProductionAPITool",
                action="get_status_for_order_ids",
                args={"order_ids": [10248]},
                status="success",
                source="Produccion",
            ),
        ],
        status="completed",
    )

    result = verify_response(response, policy=policy, data={"erp_orders": []})

    assert not result.passed
    assert "answer no usable o generico pese a status completed" in result.issues


def test_evidence_verifier_rejects_internal_todo_updates() -> None:
    policy = tool_policy("Dame un resumen del estado de los pedidos de este mes", [])
    response = QueryResponse(
        answer=(
            "Updated todo list to [{'content': 'Consultar ERP', "
            "'status': 'in_progress'}, {'content': 'Combinar datos', "
            "'status': 'pending'}]"
        ),
        sources=["ERP", "Produccion"],
        reasoning=["Consulta ERP", "Consulta produccion"],
        tool_calls=[
            ToolCallTrace(
                tool="ERPTool",
                action="get_orders_by_month",
                args={"year": 2026, "month": 5},
                status="success",
                source="ERP",
            ),
            ToolCallTrace(
                tool="ProductionAPITool",
                action="get_status_for_order_ids",
                args={"order_ids": [10248]},
                status="success",
                source="Produccion",
            ),
        ],
        status="completed",
    )

    result = verify_response(response, policy=policy, data={"erp_orders": []})

    assert not result.passed
    assert "answer no usable o generico pese a status completed" in result.issues


def test_evidence_verifier_does_not_treat_years_as_order_ids() -> None:
    policy = tool_policy("Dame un resumen del estado de los pedidos de este mes", [])
    response = QueryResponse(
        answer="En mayo de 2026 el pedido 10248 esta en curso.",
        sources=["ERP", "Produccion"],
        reasoning=["Consulta ERP", "Consulta produccion"],
        tool_calls=[
            ToolCallTrace(
                tool="ERPTool",
                action="get_orders_by_month",
                args={"year": 2026, "month": 5},
                status="success",
                source="ERP",
            ),
            ToolCallTrace(
                tool="ProductionAPITool",
                action="get_status_for_order_ids",
                args={"order_ids": [10248]},
                status="success",
                source="Produccion",
            ),
        ],
        status="completed",
    )

    result = verify_response(
        response,
        policy=policy,
        data={
            "erp_orders": [{"order_id": 10248}],
            "production_orders": [{"order_id": 10248}],
        },
    )

    assert result.passed
