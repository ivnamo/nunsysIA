from app.core.tracing import ToolCallTrace
from app.schemas.query import QueryResponse
from scripts.beta_validation_support import (
    BetaCase,
    BetaExpectation,
    BetaTurn,
    evaluate_beta_case,
    render_beta_case_report,
)


def test_evaluate_beta_case_passes_when_required_business_facts_are_present() -> None:
    beta_case = BetaCase(
        case_id="BT-X",
        title="Pedidos ALFKI",
        evaluator_expected="Debe listar pedidos pendientes.",
        turns=(
            BetaTurn(
                question="Que pedidos pendientes tiene ALFKI?",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("ERP",),
                    required_tools=("ERPTool",),
                    required_answer_terms=("10248", "10252"),
                    required_data_contains={"erp_order_ids": (10248, 10252)},
                ),
            ),
        ),
    )
    response = _response(
        answer="ALFKI tiene los pedidos pendientes 10248 y 10252.",
        sources=["ERP"],
        tool_calls=[
            ToolCallTrace(
                tool="ERPTool",
                action="get_pending_orders_by_customer",
                status="success",
                source="ERP",
            )
        ],
        data={"erp_order_ids": [10248, 10252]},
    )

    verdict = evaluate_beta_case(beta_case, [response])

    assert verdict.status == "PASS"
    assert verdict.issues == ()


def test_evaluate_beta_case_fails_on_missing_source_or_hallucination_marker() -> None:
    beta_case = BetaCase(
        case_id="BT-X",
        title="Respuesta limpia",
        evaluator_expected="Debe mantener trazabilidad y tono natural.",
        turns=(
            BetaTurn(
                question="Que pedidos estan bloqueados?",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Produccion", "ERP"),
                    required_tools=("ProductionAPITool", "ERPTool"),
                    required_answer_terms=("10252",),
                ),
            ),
        ),
    )
    response = _response(
        answer="10252 esta bloqueado sin inventar.",
        sources=["Produccion"],
        tool_calls=[
            ToolCallTrace(
                tool="ProductionAPITool",
                action="list_orders",
                status="success",
                source="Produccion",
            )
        ],
    )

    verdict = evaluate_beta_case(beta_case, [response])

    assert verdict.status == "FAIL"
    assert any("sources esperadas" in issue for issue in verdict.issues)
    assert any("tool obligatoria ausente: ERPTool" in issue for issue in verdict.issues)
    assert any("termino prohibido" in issue for issue in verdict.issues)


def test_render_beta_case_report_includes_expected_actual_and_verdict() -> None:
    beta_case = BetaCase(
        case_id="BT-X",
        title="Reporte",
        evaluator_expected="Debe mostrar comparacion esperada contra real.",
        turns=(
            BetaTurn(
                question="Pregunta de prueba",
                expectation=BetaExpectation(status="completed"),
            ),
        ),
    )
    response = _response(answer="Respuesta de prueba.")
    verdict = evaluate_beta_case(beta_case, [response])

    report = render_beta_case_report(beta_case, [response], verdict)

    assert "Resultado esperado desde el evaluador" in report
    assert "Respuesta exacta visible en Chainlit" in report
    assert "Evidencia tecnica resumida" in report
    assert "Veredicto: `PASS`" in report


def _response(
    answer: str,
    sources: list[str] | None = None,
    tool_calls: list[ToolCallTrace] | None = None,
    data: dict | None = None,
) -> QueryResponse:
    return QueryResponse(
        answer=answer,
        sources=sources or [],
        reasoning=[],
        tool_calls=tool_calls or [],
        fallbacks=[],
        confidence=0.9,
        status="completed",
        data=data,
        failure_reason=None,
    )
