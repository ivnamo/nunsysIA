from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.beta_validation_support import OBLIGATORY_BETA_CASES, BetaCase


FORBIDDEN_RAG_FALLBACKS = (
    "FALLBACK_VECTOR_STORE_IN_MEMORY",
    "FALLBACK_EMBEDDINGS_DETERMINISTIC",
)
PDFS_TO_UPLOAD = (
    "v2_contrato_marco_logistica_2026.pdf",
    "v2_anexo_penalizaciones_sla.pdf",
    "v2_procedimiento_produccion_bloqueos.pdf",
    "v2_politica_calidad_entregas.pdf",
    "v2_condiciones_comerciales_northwind.pdf",
)


@dataclass(frozen=True)
class ValidationTurn:
    question: str
    expected_status: str = "completed"
    expected_sources: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationCase:
    case_id: str
    layer: str
    title: str
    source: str
    turns: tuple[ValidationTurn, ...]


@dataclass
class TurnResult:
    question: str
    http_status: int | None
    payload: dict[str, Any] | None
    error: str | None = None


@dataclass
class CaseResult:
    case: ValidationCase
    turn_results: list[TurnResult]
    verdict: str
    issues: list[str]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta validacion Docker/API de entrega y genera Markdown."
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--production-url", default="http://localhost:8001")
    parser.add_argument("--chainlit-url", default="http://localhost:8002")
    parser.add_argument("--chroma-url", default="http://localhost:8003")
    parser.add_argument("--mode", default="deepagent")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "VALIDACION_ENTREGA.md",
    )
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    client = httpx.Client(timeout=args.timeout)
    try:
        checks = _service_checks(
            client=client,
            base_url=args.base_url,
            production_url=args.production_url,
            chainlit_url=args.chainlit_url,
            chroma_url=args.chroma_url,
        )
        reset = _reset_documents(client, args.base_url)
        if reset.get("http_status") != 200:
            raise RuntimeError(f"No se pudo resetear el indice RAG: {reset}")
        uploads = _upload_documents(client, args.base_url)
        cases = _delivery_cases()
        results = [_execute_case(client, args.base_url, args.mode, case) for case in cases]
    finally:
        client.close()

    report = _render_report(
        base_url=args.base_url,
        mode=args.mode,
        checks=checks,
        reset=reset,
        uploads=uploads,
        results=results,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    return 0 if all(result.verdict == "PASS" for result in results) else 1


def _service_checks(
    *,
    client: httpx.Client,
    base_url: str,
    production_url: str,
    chainlit_url: str,
    chroma_url: str,
) -> dict[str, str]:
    return {
        "backend": _check_url(client, f"{base_url.rstrip('/')}/health"),
        "production-api": _check_url(client, f"{production_url.rstrip('/')}/health"),
        "chainlit": _check_url(client, chainlit_url.rstrip("/")),
        "chromadb": _check_url(
            client,
            f"{chroma_url.rstrip('/')}/api/v2/heartbeat",
            accepted_statuses={200},
        ),
    }


def _check_url(
    client: httpx.Client,
    url: str,
    *,
    accepted_statuses: set[int] | None = None,
) -> str:
    accepted = accepted_statuses or {200}
    try:
        response = client.get(url)
    except Exception as exc:
        return f"ERROR: {exc}"
    if response.status_code in accepted:
        return f"OK HTTP {response.status_code}"
    return f"ERROR HTTP {response.status_code}: {response.text[:120]}"


def _reset_documents(client: httpx.Client, base_url: str) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/api/documents"
    response = client.delete(endpoint, params={"confirm": "reset-delivery-rag"})
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}
    return {
        "http_status": response.status_code,
        "status": payload.get("status"),
        "chunks_removed": payload.get("chunks_removed"),
        "fallbacks": payload.get("fallbacks"),
        "detail": payload.get("detail"),
    }


def _upload_documents(client: httpx.Client, base_url: str) -> list[dict[str, Any]]:
    uploads = []
    endpoint = f"{base_url.rstrip('/')}/api/documents/upload"
    for filename in PDFS_TO_UPLOAD:
        path = ROOT / "data" / "sample_docs" / filename
        with path.open("rb") as file:
            response = client.post(
                endpoint,
                files={"file": (filename, file, "application/pdf")},
            )
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}
        uploads.append(
            {
                "filename": filename,
                "http_status": response.status_code,
                "status": payload.get("status"),
                "chunks_indexed": payload.get("chunks_indexed"),
                "fallbacks": payload.get("fallbacks"),
            }
        )
    return uploads


def _delivery_cases() -> tuple[ValidationCase, ...]:
    required = (
        ValidationCase(
            case_id="F-ERP-01",
            layer="OBLIGATORIO",
            title="Pedidos pendientes de cliente y estado de produccion",
            source="PDF 2.1",
            turns=(
                ValidationTurn(
                    question=(
                        "Que pedidos pendientes tiene el cliente ALFKI y en que "
                        "estado de produccion estan?"
                    ),
                    expected_sources=("ERP", "Produccion"),
                    required_tools=("ERPTool", "ProductionAPITool"),
                ),
            ),
        ),
        ValidationCase(
            case_id="F-ERP-02",
            layer="OBLIGATORIO",
            title="Pedidos bloqueados y motivo",
            source="PDF 2.1",
            turns=(
                ValidationTurn(
                    question="Que pedidos estan bloqueados y cual es el motivo?",
                    expected_sources=("Produccion", "ERP"),
                    required_tools=("ProductionAPITool", "ERPTool"),
                ),
            ),
        ),
        ValidationCase(
            case_id="F-ERP-03",
            layer="OBLIGATORIO",
            title="Clientes con pedidos retrasados por produccion",
            source="PDF 2.1",
            turns=(
                ValidationTurn(
                    question=(
                        "Que clientes tienen pedidos retrasados por problemas de "
                        "produccion?"
                    ),
                    expected_sources=("Produccion", "ERP"),
                    required_tools=("ProductionAPITool", "ERPTool"),
                ),
            ),
        ),
        ValidationCase(
            case_id="F-ERP-04",
            layer="OBLIGATORIO",
            title="Resumen mensual de pedidos",
            source="PDF 2.1",
            turns=(
                ValidationTurn(
                    question="Dame un resumen del estado de los pedidos de este mes",
                    expected_sources=("ERP", "Produccion"),
                    required_tools=("ERPTool", "ProductionAPITool"),
                ),
            ),
        ),
        ValidationCase(
            case_id="F-RAG-01",
            layer="OBLIGATORIO",
            title="Plazos de entrega en documento",
            source="PDF 2.2",
            turns=(
                ValidationTurn(
                    question="Que dice este documento sobre plazos de entrega?",
                    expected_sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                ),
            ),
        ),
        ValidationCase(
            case_id="F-RAG-02",
            layer="OBLIGATORIO",
            title="Resumen de puntos clave del contrato",
            source="PDF 2.2",
            turns=(
                ValidationTurn(
                    question="Resume los puntos clave del contrato",
                    expected_sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                ),
            ),
        ),
        ValidationCase(
            case_id="F-RAG-03",
            layer="OBLIGATORIO",
            title="Penalizaciones por retrasos",
            source="PDF 2.2",
            turns=(
                ValidationTurn(
                    question="Hay alguna penalizacion por retrasos?",
                    expected_sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                ),
            ),
        ),
    )
    return required + tuple(_beta_case_to_validation(case) for case in _extra_beta_cases())


def _extra_beta_cases() -> tuple[BetaCase, ...]:
    required_beta_ids = {"BT-01", "BT-02", "BT-03", "BT-04", "BT-05", "BT-06", "BT-07"}
    return tuple(
        case for case in OBLIGATORY_BETA_CASES if case.case_id not in required_beta_ids
    )


def _beta_case_to_validation(case: BetaCase) -> ValidationCase:
    turns = tuple(
        ValidationTurn(
            question=turn.question,
            expected_status=turn.expectation.status,
            expected_sources=turn.expectation.sources or (),
            required_tools=turn.expectation.required_tools,
        )
        for turn in case.turns
    )
    return ValidationCase(
        case_id=case.case_id,
        layer="ADICIONAL",
        title=case.title,
        source="Beta validation",
        turns=turns,
    )


def _execute_case(
    client: httpx.Client,
    base_url: str,
    mode: str,
    case: ValidationCase,
) -> CaseResult:
    results = []
    issues: list[str] = []
    conversation_id = f"delivery-{case.case_id.lower()}-{int(time.time())}"
    endpoint = f"{base_url.rstrip('/')}/api/query"
    for index, turn in enumerate(case.turns, start=1):
        try:
            response = client.post(
                endpoint,
                json={
                    "question": turn.question,
                    "conversation_id": conversation_id,
                    "mode": mode,
                    "include_citation_previews": False,
                },
            )
            payload = response.json()
        except Exception as exc:
            results.append(TurnResult(turn.question, None, None, str(exc)))
            issues.append(f"turno {index}: error de transporte o JSON: {exc}")
            continue

        results.append(TurnResult(turn.question, response.status_code, payload))
        issues.extend(_evaluate_turn(index, turn, response.status_code, payload))

    return CaseResult(
        case=case,
        turn_results=results,
        verdict="PASS" if not issues else "FAIL",
        issues=issues,
    )


def _evaluate_turn(
    index: int,
    turn: ValidationTurn,
    http_status: int,
    payload: dict[str, Any],
) -> list[str]:
    issues = []
    prefix = f"turno {index}"
    if http_status != 200:
        issues.append(f"{prefix}: HTTP esperado 200, recibido {http_status}")
        return issues
    if payload.get("status") != turn.expected_status:
        issues.append(
            f"{prefix}: status esperado {turn.expected_status!r}, "
            f"recibido {payload.get('status')!r}"
        )
    sources = tuple(payload.get("sources") or ())
    for source in turn.expected_sources:
        if source not in sources:
            issues.append(f"{prefix}: fuente obligatoria ausente: {source}")
    tools = [call.get("tool") for call in payload.get("tool_calls") or []]
    for tool in turn.required_tools:
        if tool not in tools:
            issues.append(f"{prefix}: tool obligatoria ausente: {tool}")
    for fallback in _fallback_candidates(payload):
        if any(marker in fallback for marker in FORBIDDEN_RAG_FALLBACKS):
            issues.append(f"{prefix}: fallback RAG prohibido: {fallback}")
    if not str(payload.get("answer") or "").strip():
        issues.append(f"{prefix}: answer vacio")
    return issues


def _fallback_candidates(payload: dict[str, Any]) -> list[str]:
    candidates = [str(value) for value in payload.get("fallbacks") or []]
    for call in payload.get("tool_calls") or []:
        summary = call.get("output_summary")
        if summary:
            candidates.append(str(summary))
    rag = (payload.get("data") or {}).get("rag") if isinstance(payload.get("data"), dict) else None
    if isinstance(rag, dict):
        candidates.extend(str(value) for value in rag.get("fallbacks") or [])
    return candidates


def _render_report(
    *,
    base_url: str,
    mode: str,
    checks: dict[str, str],
    reset: dict[str, Any],
    uploads: list[dict[str, Any]],
    results: list[CaseResult],
) -> str:
    totals = {
        "PASS": sum(1 for result in results if result.verdict == "PASS"),
        "FAIL": sum(1 for result in results if result.verdict == "FAIL"),
    }
    lines = [
        "# Validacion de entrega Docker/API",
        "",
        f"Fecha de ejecucion: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Endpoint validado: `{base_url.rstrip('/')}/api/query`",
        f"Modo agentic: `{mode}`",
        "",
        (
            f"Resultado global: PASS={totals['PASS']}, FAIL={totals['FAIL']}, "
            f"casos={len(results)}."
        ),
        "",
        "## Servicios",
        "",
        "| Servicio | Estado |",
        "| --- | --- |",
    ]
    for name, status in checks.items():
        lines.append(f"| {name} | {status} |")

    lines.extend(
        [
            "",
            "## Reset RAG",
            "",
            "| HTTP | Estado | Chunks eliminados | Fallbacks | Detail |",
            "| ---: | --- | ---: | --- | --- |",
            (
                "| {http_status} | {status} | {chunks_removed} | {fallbacks} | {detail} |"
            ).format(
                http_status=reset.get("http_status"),
                status=reset.get("status"),
                chunks_removed=reset.get("chunks_removed"),
                fallbacks=_inline_json(reset.get("fallbacks")),
                detail=reset.get("detail") or "",
            ),
            "",
            "## PDFs indexados",
            "",
            "| PDF | HTTP | Estado | Chunks | Fallbacks |",
            "| --- | ---: | --- | ---: | --- |",
        ]
    )
    for upload in uploads:
        lines.append(
            "| {filename} | {http_status} | {status} | {chunks_indexed} | {fallbacks} |".format(
                filename=upload["filename"],
                http_status=upload["http_status"],
                status=upload.get("status"),
                chunks_indexed=upload.get("chunks_indexed"),
                fallbacks=_inline_json(upload.get("fallbacks")),
            )
        )

    lines.extend(
        [
            "",
            "## Tabla resumen",
            "",
            "| ID | Capa | Fuente | Veredicto | HTTP/status | Fuentes | Tools |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for result in results:
        status_text = _status_text(result)
        sources_text = _sources_text(result)
        tools_text = _tools_text(result)
        lines.append(
            "| {case_id} | {layer} | {source} | {verdict} | {status} | {sources} | {tools} |".format(
                case_id=result.case.case_id,
                layer=result.case.layer,
                source=result.case.source,
                verdict=result.verdict,
                status=status_text,
                sources=sources_text,
                tools=tools_text,
            )
        )

    lines.extend(["", "## Respuestas", ""])
    for result in results:
        lines.extend(_render_case_result(result))
    return "\n".join(lines) + "\n"


def _render_case_result(result: CaseResult) -> list[str]:
    lines = [
        f"### {result.case.case_id} - {result.verdict} - {result.case.title}",
        "",
    ]
    if result.issues:
        lines.append("Incidencias:")
        lines.extend(f"- {issue}" for issue in result.issues)
        lines.append("")

    for index, turn in enumerate(result.turn_results, start=1):
        payload = turn.payload or {}
        lines.extend(
            [
                f"Pregunta {index}: `{turn.question}`",
                "",
                f"HTTP: `{turn.http_status}` | status: `{payload.get('status')}`",
                f"Fuentes: `{_inline_json(payload.get('sources'))}`",
                f"Tools: `{_inline_json([call.get('tool') for call in payload.get('tool_calls') or []])}`",
                f"Fallbacks: `{_inline_json(payload.get('fallbacks'))}`",
                "",
                "Respuesta:",
                "",
                "```markdown",
                str(payload.get("answer") or turn.error or ""),
                "```",
                "",
            ]
        )
        reasoning = payload.get("reasoning") or []
        if reasoning:
            lines.extend(["Pasos:", ""])
            lines.extend(f"- {step}" for step in reasoning)
            lines.append("")
        rag = (payload.get("data") or {}).get("rag") if isinstance(payload.get("data"), dict) else None
        if isinstance(rag, dict):
            lines.extend(
                [
                    "Evidencia RAG:",
                    "",
                    f"- documentos: `{_inline_json(rag.get('documents'))}`",
                    f"- chunks_count: `{rag.get('chunks_count')}`",
                    "",
                ]
            )
    return lines


def _status_text(result: CaseResult) -> str:
    parts = []
    for turn in result.turn_results:
        payload_status = (turn.payload or {}).get("status")
        parts.append(f"{turn.http_status}/{payload_status}")
    return "<br>".join(parts)


def _sources_text(result: CaseResult) -> str:
    values: list[str] = []
    for turn in result.turn_results:
        for source in (turn.payload or {}).get("sources") or []:
            if source not in values:
                values.append(source)
    return ", ".join(values) or "-"


def _tools_text(result: CaseResult) -> str:
    values: list[str] = []
    for turn in result.turn_results:
        for call in (turn.payload or {}).get("tool_calls") or []:
            tool = call.get("tool")
            if tool and tool not in values:
                values.append(tool)
    return ", ".join(values) or "-"


def _inline_json(value: Any) -> str:
    return json.dumps(value or [], ensure_ascii=False)


if __name__ == "__main__":
    raise SystemExit(main())
