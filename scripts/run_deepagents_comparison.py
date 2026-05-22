from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agents.deepagents_adapter import deepagents_is_available
from app.agents.deepagents_service import (
    create_deepagents_query_service,
)
from app.agents.service import QueryWorkflowService
from app.core.config import get_settings
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.production.client import ProductionAPIClient
from app.schemas.query import QueryRequest, QueryResponse
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.erp_tool import ERPTool
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool
from scripts.run_beta_validation import (
    V2_DOCUMENTS,
    _create_real_chat_model,
    _create_real_document_service,
    _production_transport,
    _real_llm_timeout_seconds,
)


@dataclass(frozen=True)
class DeepAgentsComparisonCase:
    case_id: str
    title: str
    turns: tuple[str, ...]
    required_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeepAgentsComparisonResult:
    case: DeepAgentsComparisonCase
    stable_responses: tuple[QueryResponse, ...]
    deepagents_responses: tuple[QueryResponse, ...]
    status: str
    issues: tuple[str, ...]


COMPARISON_CASES = (
    DeepAgentsComparisonCase(
        case_id="DA-01",
        title="ALFKI pendientes y estado de produccion",
        turns=(
            "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
        ),
        required_terms=("10248", "10252"),
    ),
    DeepAgentsComparisonCase(
        case_id="DA-02",
        title="Bloqueos de produccion cruzados con ERP",
        turns=("Cruza produccion con ERP y dime clientes afectados por bloqueos.",),
        required_terms=("10252", "10312"),
    ),
    DeepAgentsComparisonCase(
        case_id="DA-03",
        title="Penalizacion potencial con documento contractual",
        turns=("Dame los pedidos que puedan generar penalizacion y dime por que.",),
        required_terms=("10301",),
    ),
    DeepAgentsComparisonCase(
        case_id="DA-04",
        title="Follow-up conversacional con conversation_id",
        turns=(
            "Que pedidos pendientes tiene el cliente ALFKI?",
            "Y en que estado estan?",
        ),
        required_terms=("10248", "10252"),
    ),
    DeepAgentsComparisonCase(
        case_id="DA-05",
        title="Pregunta documental sin evidencia",
        turns=("Que dice el contrato sobre criptomonedas?",),
        required_terms=("criptomonedas",),
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compara el workflow estable contra el flujo experimental Deep Agents."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "DEEPAGENTS_COMPARISON_REPORT.md",
        help="Ruta del informe Markdown.",
    )
    args = parser.parse_args()

    if os.getenv("RUN_DEEPAGENTS_COMPARISON") != "1":
        print(
            "RUN_DEEPAGENTS_COMPARISON=1 no esta configurado. "
            "Este runner invoca LLM real via Deep Agents.",
            file=sys.stderr,
        )
        return 2

    if not deepagents_is_available():
        print(
            "deepagents no esta instalado en este entorno. "
            "Usa requirements-deepagents.txt o el venv temporal compatible.",
            file=sys.stderr,
        )
        return 2

    try:
        workflow = _build_comparison_workflow_service()
        deepagents_service = create_deepagents_query_service(
            settings=get_settings(),
            workflow=workflow,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    results = []
    for comparison_case in COMPARISON_CASES:
        try:
            results.append(
                _run_case(
                    comparison_case=comparison_case,
                    workflow=workflow,
                    deepagents_service=deepagents_service,
                )
            )
        except Exception as exc:
            results.append(
                DeepAgentsComparisonResult(
                    case=comparison_case,
                    stable_responses=(),
                    deepagents_responses=(),
                    status="BLOCKER",
                    issues=(str(exc),),
                )
            )

    report = _render_report(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    totals = _totals(results)
    return 0 if totals["FAIL"] == 0 and totals["BLOCKER"] == 0 else 1


def _build_comparison_workflow_service() -> QueryWorkflowService:
    chat_model = _create_real_chat_model()
    connection = create_sqlite_connection(check_same_thread=False)
    load_seed_sql(connection)
    repository = NorthwindRepository(connection)

    production_client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=_production_transport(),
    )
    document_service = _create_real_document_service(V2_DOCUMENTS)

    return QueryWorkflowService(
        erp_tool=ERPTool(repository),
        production_tool=ProductionAPITool(production_client),
        erp_query_tool=ERPQueryTool(repository),
        production_query_tool=ProductionQueryTool(production_client),
        rag_tool=DocumentRAGTool(
            vector_store=document_service.vector_store,
            embedding_model=document_service.embedding_model,
        ),
        chat_model=chat_model,
        llm_timeout_seconds=_real_llm_timeout_seconds(),
    )


def _run_case(
    comparison_case: DeepAgentsComparisonCase,
    workflow,
    deepagents_service,
) -> DeepAgentsComparisonResult:
    stable_responses = []
    deepagents_responses = []
    stable_conversation_id = f"deepcompare-stable-{comparison_case.case_id.lower()}"
    deepagents_conversation_id = f"deepcompare-deep-{comparison_case.case_id.lower()}"

    for question in comparison_case.turns:
        stable_responses.append(
            workflow.run(
                QueryRequest(
                    question=question,
                    conversation_id=stable_conversation_id,
                )
            )
        )
        deepagents_responses.append(
            deepagents_service.run(
                QueryRequest(
                    question=question,
                    conversation_id=deepagents_conversation_id,
                )
            )
        )

    issues = _compare_last_responses(
        comparison_case,
        stable_responses[-1],
        deepagents_responses[-1],
    )
    status = "PASS" if not issues else "PARTIAL"
    if any(issue.startswith("BLOCKER") for issue in issues):
        status = "BLOCKER"
    return DeepAgentsComparisonResult(
        case=comparison_case,
        stable_responses=tuple(stable_responses),
        deepagents_responses=tuple(deepagents_responses),
        status=status,
        issues=tuple(issues),
    )


def _compare_last_responses(
    comparison_case: DeepAgentsComparisonCase,
    stable_response: QueryResponse,
    deepagents_response: QueryResponse,
) -> list[str]:
    issues = []
    if deepagents_response.status != stable_response.status:
        issues.append(
            f"status distinto: estable={stable_response.status}, "
            f"deepagents={deepagents_response.status}"
        )
    if deepagents_response.sources != stable_response.sources:
        issues.append(
            f"sources distintas: estable={stable_response.sources}, "
            f"deepagents={deepagents_response.sources}"
        )
    stable_tools = [call.tool for call in stable_response.tool_calls]
    deepagents_tools = [call.tool for call in deepagents_response.tool_calls]
    if deepagents_tools != stable_tools:
        issues.append(
            f"tool_calls distintas: estable={stable_tools}, "
            f"deepagents={deepagents_tools}"
        )
    answer_text = deepagents_response.answer.lower()
    for term in comparison_case.required_terms:
        if term.lower() not in answer_text:
            issues.append(f"falta termino esperado en Deep Agents: {term}")
    return issues


def _render_report(results: list[DeepAgentsComparisonResult]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    totals = _totals(results)
    sections = [
        "# Deep Agents Comparison Report",
        "",
        f"Fecha de ejecucion: {generated_at}",
        "",
        (
            "Resultado global: "
            f"PASS={totals['PASS']}, PARTIAL={totals['PARTIAL']}, "
            f"FAIL={totals['FAIL']}, BLOCKER={totals['BLOCKER']}."
        ),
        "",
        "Runtime:",
        "",
        "- Workflow estable: `QueryWorkflowService`.",
        "- Flujo experimental: `DeepAgentsQueryService`.",
        "- Deep Agents usa el workflow estable como tool auditable.",
        "- Modelo Deep Agents: `DEEPAGENTS_MODEL` o valor por defecto.",
        "",
    ]
    for result in results:
        sections.extend(_render_case(result))
    return "\n".join(sections)


def _render_case(result: DeepAgentsComparisonResult) -> list[str]:
    stable_response = result.stable_responses[-1] if result.stable_responses else None
    deepagents_response = (
        result.deepagents_responses[-1] if result.deepagents_responses else None
    )
    lines = [
        f"## {result.case.case_id} - {result.case.title}",
        "",
        f"Veredicto: **{result.status}**",
        "",
        "Preguntas:",
        "",
    ]
    lines.extend([f"- {turn}" for turn in result.case.turns])
    lines.extend(["", "Incidencias:", ""])
    if result.issues:
        lines.extend([f"- {issue}" for issue in result.issues])
    else:
        lines.append("- Sin divergencias criticas.")
    lines.extend(["", "Respuesta estable:", ""])
    lines.append(_response_summary(stable_response))
    lines.extend(["", "Respuesta Deep Agents:", ""])
    lines.append(_response_summary(deepagents_response))
    lines.append("")
    return lines


def _response_summary(response: QueryResponse | None) -> str:
    if response is None:
        return "- No disponible."
    tools = [call.tool for call in response.tool_calls]
    return "\n".join(
        [
            f"- status: `{response.status}`",
            f"- sources: `{list(response.sources)}`",
            f"- tools: `{tools}`",
            f"- fallbacks: `{response.fallbacks}`",
            f"- answer: {response.answer}",
        ]
    )


def _totals(results: list[DeepAgentsComparisonResult]) -> dict[str, int]:
    totals = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "BLOCKER": 0}
    for result in results:
        totals[result.status] = totals.get(result.status, 0) + 1
    return totals


if __name__ == "__main__":
    raise SystemExit(main())
