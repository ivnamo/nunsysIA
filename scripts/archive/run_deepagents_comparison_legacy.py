from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agents.deepagents_adapter import deepagents_is_available
from app.agents.deepagents_service import (
    create_deepagents_query_service,
)
from app.agents.deepagents_tools_service import create_deepagents_tools_query_service
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
from scripts.archive.run_beta_validation_legacy import (
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
    sidecar_responses: tuple[QueryResponse, ...]
    direct_tools_responses: tuple[QueryResponse, ...]
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
        default=ROOT
        / "docs"
        / "archive"
        / "validation"
        / "DEEPAGENTS_COMPARISON_REPORT.md",
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
            "Instala requirements.txt o usa un venv compatible.",
            file=sys.stderr,
        )
        return 2

    try:
        workflow, sidecar_service, direct_tools_service = _build_comparison_services()
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
                    sidecar_service=sidecar_service,
                    direct_tools_service=direct_tools_service,
                )
            )
        except Exception as exc:
            results.append(
                DeepAgentsComparisonResult(
                    case=comparison_case,
                    stable_responses=(),
                    sidecar_responses=(),
                    direct_tools_responses=(),
                    status="BLOCKER",
                    issues=(str(exc),),
                )
            )

    report = _render_report(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    totals = _totals(results)
    return 0 if totals["FAIL"] == 0 and totals["BLOCKER"] == 0 else 1


def _build_comparison_services() -> tuple[QueryWorkflowService, object, object]:
    chat_model = _create_real_chat_model()
    connection = create_sqlite_connection(check_same_thread=False)
    load_seed_sql(connection)
    repository = NorthwindRepository(connection)
    settings = get_settings()

    production_client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=_production_transport(),
    )
    document_service = _create_real_document_service(V2_DOCUMENTS)
    erp_tool = ERPTool(repository)
    production_tool = ProductionAPITool(production_client)
    erp_query_tool = ERPQueryTool(repository)
    production_query_tool = ProductionQueryTool(production_client)
    rag_tool = DocumentRAGTool(
        vector_store=document_service.vector_store,
        embedding_model=document_service.embedding_model,
    )

    workflow = QueryWorkflowService(
        erp_tool=erp_tool,
        production_tool=production_tool,
        erp_query_tool=erp_query_tool,
        production_query_tool=production_query_tool,
        rag_tool=rag_tool,
        chat_model=chat_model,
        llm_timeout_seconds=_real_llm_timeout_seconds(),
    )
    sidecar_service = create_deepagents_query_service(
        settings=settings,
        workflow=workflow,
    )
    direct_tools_service = create_deepagents_tools_query_service(
        settings=settings,
        erp_tool=erp_tool,
        production_tool=production_tool,
        erp_query_tool=erp_query_tool,
        production_query_tool=production_query_tool,
        rag_tool=rag_tool,
    )
    return workflow, sidecar_service, direct_tools_service


def _run_case(
    comparison_case: DeepAgentsComparisonCase,
    workflow,
    sidecar_service,
    direct_tools_service,
) -> DeepAgentsComparisonResult:
    stable_responses = []
    sidecar_responses = []
    direct_tools_responses = []
    stable_conversation_id = f"deepcompare-stable-{comparison_case.case_id.lower()}"
    sidecar_conversation_id = f"deepcompare-sidecar-{comparison_case.case_id.lower()}"
    direct_tools_conversation_id = (
        f"deepcompare-tools-{comparison_case.case_id.lower()}"
    )

    for question in comparison_case.turns:
        stable_responses.append(
            workflow.run(
                QueryRequest(
                    question=question,
                    conversation_id=stable_conversation_id,
                )
            )
        )
        sidecar_responses.append(
            sidecar_service.run(
                QueryRequest(
                    question=question,
                    conversation_id=sidecar_conversation_id,
                )
            )
        )
        direct_tools_responses.append(
            direct_tools_service.run(
                QueryRequest(
                    question=question,
                    conversation_id=direct_tools_conversation_id,
                )
            )
        )

    sidecar_issues = _compare_last_responses(
        comparison_case,
        stable_responses[-1],
        sidecar_responses[-1],
        label="sidecar",
    )
    direct_tools_issues = _compare_last_responses(
        comparison_case,
        stable_responses[-1],
        direct_tools_responses[-1],
        label="tools",
    )
    issues = [*sidecar_issues, *direct_tools_issues]
    status = "PASS" if not _has_acceptance_issues(issues) else "PARTIAL"
    if any(issue.startswith("BLOCKER") for issue in issues):
        status = "BLOCKER"
    return DeepAgentsComparisonResult(
        case=comparison_case,
        stable_responses=tuple(stable_responses),
        sidecar_responses=tuple(sidecar_responses),
        direct_tools_responses=tuple(direct_tools_responses),
        status=status,
        issues=tuple(issues),
    )


def _compare_last_responses(
    comparison_case: DeepAgentsComparisonCase,
    stable_response: QueryResponse,
    compared_response: QueryResponse,
    label: str,
) -> list[str]:
    issues = []
    if compared_response.status != stable_response.status:
        issues.append(
            f"SEMANTIC {label}: status distinto: estable={stable_response.status}, "
            f"{label}={compared_response.status}"
        )
    if set(compared_response.sources) != set(stable_response.sources):
        issues.append(
            f"SEMANTIC {label}: sources distintas: estable={stable_response.sources}, "
            f"{label}={compared_response.sources}"
        )
    elif compared_response.sources != stable_response.sources:
        issues.append(
            f"TRACE {label}: orden de sources distinto: estable={stable_response.sources}, "
            f"{label}={compared_response.sources}"
        )
    stable_tools = [call.tool for call in stable_response.tool_calls]
    compared_tools = [call.tool for call in compared_response.tool_calls]
    if compared_tools != stable_tools:
        issues.append(
            f"TRACE {label}: tool_calls distintas: estable={stable_tools}, "
            f"{label}={compared_tools}"
        )
    rag_calls = len([tool for tool in compared_tools if tool == "DocumentRAGTool"])
    if label == "tools" and rag_calls > 1:
        issues.append(
            f"EFFICIENCY {label}: sobreconsulta RAG: {rag_calls} llamadas DocumentRAGTool"
        )
    if label == "tools" and len(compared_tools) > max(len(stable_tools) * 2, 8):
        issues.append(
            f"EFFICIENCY {label}: exceso de tool calls: estable={len(stable_tools)}, "
            f"{label}={len(compared_tools)}"
        )
    answer_text = compared_response.answer.lower()
    for term in comparison_case.required_terms:
        if term.lower() not in answer_text:
            issues.append(f"SEMANTIC {label}: falta termino esperado: {term}")
    return issues


def _has_acceptance_issues(issues: list[str]) -> bool:
    acceptance_prefixes = ("SEMANTIC", "EFFICIENCY", "GUARDRAIL", "BLOCKER")
    return any(issue.startswith(acceptance_prefixes) for issue in issues)


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
        "- Flujo sidecar: `DeepAgentsQueryService`.",
        "- Flujo tools: `DeepAgentsToolsQueryService`.",
        "- Sidecar usa el workflow estable como tool auditable.",
        "- Tools expone ERP, Produccion, RAG y Memoria como tools individuales.",
        "- Tools conserva `write_todos` y excluye filesystem, shell y subagentes.",
        "- El veredicto separa incidencias semanticas/eficiencia de diferencias de traza.",
        "- Modelo Deep Agents: `DEEPAGENTS_MODEL` o valor por defecto.",
        "",
    ]
    for result in results:
        sections.extend(_render_case(result))
    return "\n".join(sections)


def _render_case(result: DeepAgentsComparisonResult) -> list[str]:
    stable_response = result.stable_responses[-1] if result.stable_responses else None
    sidecar_response = result.sidecar_responses[-1] if result.sidecar_responses else None
    direct_tools_response = (
        result.direct_tools_responses[-1] if result.direct_tools_responses else None
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
    lines.extend(["", "Respuesta Deep Agents sidecar:", ""])
    lines.append(_response_summary(sidecar_response))
    lines.extend(["", "Respuesta Deep Agents tools:", ""])
    lines.append(_response_summary(direct_tools_response))
    lines.append("")
    return lines


def _response_summary(response: QueryResponse | None) -> str:
    if response is None:
        return "- No disponible."
    tools = [call.tool for call in response.tool_calls]
    answer = "\n".join(line.rstrip() for line in response.answer.splitlines()).strip()
    lines = [
        f"- status: `{response.status}`",
        f"- sources: `{list(response.sources)}`",
        f"- tools: `{tools}`",
        f"- fallbacks: `{response.fallbacks}`",
    ]
    planning = (response.data or {}).get("deepagents_planning")
    if isinstance(planning, dict):
        lines.append(f"- deepagents_planning: `{planning}`")
    lines.append(f"- answer: {answer}")
    return "\n".join(lines)


def _totals(results: list[DeepAgentsComparisonResult]) -> dict[str, int]:
    totals = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "BLOCKER": 0}
    for result in results:
        totals[result.status] = totals.get(result.status, 0) + 1
    return totals


if __name__ == "__main__":
    raise SystemExit(main())
