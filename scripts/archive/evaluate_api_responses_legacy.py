from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    question: str
    expected_sources: tuple[str, ...]
    expected_behavior: str
    required_terms: tuple[str, ...] = ()
    required_any_terms: tuple[tuple[str, ...], ...] = ()
    forbidden_answer_terms: tuple[str, ...] = (
        "```",
        '"answer"',
        "chunk_id",
        "metadata",
        "pagina 1 de",
        "pagina 2 de",
        "pagina 3 de",
        "pagina 4 de",
    )
    conversation_key: str | None = None
    critical: bool = True


@dataclass
class ScoreBreakdown:
    functional: int
    information_quality: int
    traceability: int
    human_wording: int
    technical_robustness: int
    issues: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            self.functional
            + self.information_quality
            + self.traceability
            + self.human_wording
            + self.technical_robustness
        )


CASES: tuple[EvaluationCase, ...] = (
    EvaluationCase(
        case_id="1",
        question="¿Qué pedidos pendientes tiene el cliente ALFKI y en qué estado de producción están?",
        expected_sources=("ERP", "Produccion"),
        expected_behavior="Debe listar pedidos pendientes de ALFKI y cruzarlos con estado de produccion.",
        required_terms=("10248", "10252"),
        required_any_terms=(("ALFKI", "Alfreds Futterkiste"), ("pendiente", "pending")),
    ),
    EvaluationCase(
        case_id="2",
        question="¿Qué pedidos están bloqueados y cuál es el motivo?",
        expected_sources=("Produccion", "ERP"),
        expected_behavior="Debe listar pedidos bloqueados, motivo y contexto ERP del pedido/cliente.",
        required_terms=("10252", "10312"),
        required_any_terms=(("Falta de material", "material"), ("Falta de capacidad", "capacidad")),
    ),
    EvaluationCase(
        case_id="3",
        question="¿Qué clientes tienen pedidos retrasados por problemas de producción?",
        expected_sources=("Produccion", "ERP"),
        expected_behavior="Debe identificar pedidos retrasados y clientes ERP asociados.",
        required_terms=("10301",),
        required_any_terms=(("ANATR", "Ana Trujillo"), ("averia", "retras")),
    ),
    EvaluationCase(
        case_id="4",
        question="Dame un resumen del estado de los pedidos de este mes",
        expected_sources=("ERP", "Produccion"),
        expected_behavior="Debe resumir pedidos del mes actual de prueba y distribucion de estados.",
        required_terms=("10248", "10252", "10255", "10301", "10312"),
        required_any_terms=(("mayo", "2026-05", "mes"), ("bloqueado", "bloqueados"), ("retrasado", "retrasados")),
    ),
    EvaluationCase(
        case_id="5",
        question="¿Qué dice este documento sobre plazos de entrega?",
        expected_sources=("Documentos",),
        expected_behavior="Debe usar RAG y redactar una respuesta humana sobre plazos documentales.",
        required_terms=("entrega",),
        required_any_terms=(("5 dias", "5 días", "cinco dias", "cinco días"), ("48 horas", "urgente", "urgentes")),
    ),
    EvaluationCase(
        case_id="6",
        question="Resume los puntos clave del contrato",
        expected_sources=("Documentos",),
        expected_behavior="Debe resumir el contrato con evidencia documental y sin pegar chunks.",
        required_terms=("contrato",),
        required_any_terms=(("logistica", "logística"), ("plazo", "entrega"), ("penaliz", "SLA")),
    ),
    EvaluationCase(
        case_id="7",
        question="¿Hay alguna penalización por retrasos?",
        expected_sources=("Documentos",),
        expected_behavior="Debe usar documentos para explicar condiciones de penalizacion por retrasos.",
        required_terms=("penaliz", "retras"),
        required_any_terms=(("2%", "5%", "porcentaje"), ("SLA", "contrato", "documento")),
    ),
    EvaluationCase(
        case_id="8a",
        question="¿Qué pedidos pendientes tiene el cliente ALFKI y en qué estado de producción están?",
        expected_sources=("ERP", "Produccion"),
        expected_behavior="Primer turno de memoria: debe fijar el contexto de pedidos ALFKI.",
        required_terms=("10248", "10252"),
        required_any_terms=(("ALFKI", "Alfreds Futterkiste"),),
        conversation_key="memory-alfki",
    ),
    EvaluationCase(
        case_id="8b",
        question="¿Y cuáles de esos pedidos están bloqueados?",
        expected_sources=("Memoria", "Produccion"),
        expected_behavior="Segundo turno: debe resolver 'esos pedidos' usando conversation_id.",
        required_terms=("10252",),
        required_any_terms=(("bloqueado", "blocked"), ("material", "Falta de material")),
        conversation_key="memory-alfki",
    ),
    EvaluationCase(
        case_id="8c",
        question="¿Cuál es el impacto económico de esos?",
        expected_sources=("Memoria", "ERP"),
        expected_behavior="Tercer turno: debe calcular impacto economico de los bloqueados previos.",
        required_terms=("10252",),
        required_any_terms=(("1863", "1.863", "1,863"), ("impacto", "importe", "economico", "económico")),
        conversation_key="memory-alfki",
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evalua de forma critica POST /api/query contra una API Dockerizada."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "http://localhost:8000"),
        help="URL base de la API. Ejemplo local: http://localhost:8000. En Docker: http://backend:8000.",
    )
    parser.add_argument("--endpoint", default="/api/query")
    parser.add_argument("--health-endpoint", default="/health")
    parser.add_argument("--mode", default=os.getenv("AGENT_MODE", "deepagent"))
    parser.add_argument("--output", type=Path, default=Path("reports/api_evaluation.md"))
    parser.add_argument("--raw-output", type=Path, default=Path("reports/raw_responses.json"))
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--health-timeout-seconds", type=float, default=180.0)
    parser.add_argument(
        "--docker-command",
        default=os.getenv("EVALUATOR_DOCKER_COMMAND", "docker compose --profile eval up --build evaluator"),
    )
    parser.add_argument(
        "--compose-config-path",
        type=Path,
        default=Path("reports/docker_compose_config.txt"),
        help="Archivo opcional con salida de 'docker compose config'.",
    )
    args = parser.parse_args()

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)

    health = wait_for_api(
        base_url=args.base_url,
        health_endpoint=args.health_endpoint,
        timeout_seconds=args.health_timeout_seconds,
    )

    records: list[dict[str, Any]] = []
    if health["ok"]:
        records = run_cases(
            base_url=args.base_url,
            endpoint=args.endpoint,
            mode=args.mode,
            timeout_seconds=args.timeout_seconds,
        )
    else:
        records = [
            {
                "case_id": case.case_id,
                "question": case.question,
                "http_status": None,
                "elapsed_ms": 0,
                "payload": {},
                "response_json": None,
                "response_text": "",
                "error": "La API no levanto o no respondio al healthcheck en Docker.",
                "retried_without_mode": False,
            }
            for case in CASES
        ]

    evaluations = [
        {
            "case": case,
            "record": record,
            "score": evaluate_record(case, record),
        }
        for case, record in zip(CASES, records, strict=True)
    ]

    raw_payload = {
        "generated_at": started_at,
        "base_url": args.base_url,
        "endpoint": args.endpoint,
        "mode": args.mode,
        "health": health,
        "records": records,
        "scores": [
            {
                "case_id": item["case"].case_id,
                "score": item["score"].total,
                "breakdown": {
                    "functional": item["score"].functional,
                    "information_quality": item["score"].information_quality,
                    "traceability": item["score"].traceability,
                    "human_wording": item["score"].human_wording,
                    "technical_robustness": item["score"].technical_robustness,
                },
                "issues": item["score"].issues,
            }
            for item in evaluations
        ],
    }
    args.raw_output.write_text(
        json.dumps(raw_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )

    report = render_report(
        generated_at=started_at,
        docker_command=args.docker_command,
        base_url=args.base_url,
        endpoint=args.endpoint,
        mode=args.mode,
        health=health,
        evaluations=evaluations,
        raw_output=args.raw_output,
        compose_config_path=args.compose_config_path,
    )
    args.output.write_text(report, encoding="utf-8", newline="\n")

    average = average_score(evaluations)
    has_severe_failure = (not health["ok"]) or any(
        item["score"].total < 14 for item in evaluations
    )
    if has_severe_failure or average < 18:
        print(
            f"Evaluacion completada con riesgos: media={average:.1f}/25. "
            f"Informe: {args.output}",
            file=sys.stderr,
        )
        return 1

    print(
        f"Evaluacion completada: media={average:.1f}/25. Informe: {args.output}",
        file=sys.stderr,
    )
    return 0


def wait_for_api(
    *,
    base_url: str,
    health_endpoint: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    url = join_url(base_url, health_endpoint)
    attempts = 0
    last_error = ""
    while time.monotonic() < deadline:
        attempts += 1
        try:
            response = httpx.get(url, timeout=5.0)
            if 200 <= response.status_code < 300:
                return {
                    "ok": True,
                    "url": url,
                    "http_status": response.status_code,
                    "attempts": attempts,
                    "body": safe_json_or_text(response),
                    "error": None,
                }
            last_error = f"HTTP {response.status_code}: {response.text[:300]}"
        except Exception as exc:  # noqa: BLE001 - diagnostic runner
            last_error = repr(exc)
        time.sleep(3)
    return {
        "ok": False,
        "url": url,
        "http_status": None,
        "attempts": attempts,
        "body": None,
        "error": last_error or "timeout",
    }


def run_cases(
    *,
    base_url: str,
    endpoint: str,
    mode: str | None,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    client = httpx.Client(timeout=httpx.Timeout(timeout_seconds))
    conversation_ids: dict[str, str] = {
        "memory-alfki": f"eval-memory-alfki-{uuid4().hex[:8]}",
    }
    records: list[dict[str, Any]] = []
    try:
        for case in CASES:
            conversation_id = (
                conversation_ids[case.conversation_key]
                if case.conversation_key
                else f"eval-{case.case_id}-{uuid4().hex[:8]}"
            )
            records.append(
                post_query(
                    client=client,
                    url=join_url(base_url, endpoint),
                    case=case,
                    conversation_id=conversation_id,
                    mode=mode,
                )
            )
    finally:
        client.close()
    return records


def post_query(
    *,
    client: httpx.Client,
    url: str,
    case: EvaluationCase,
    conversation_id: str,
    mode: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "question": case.question,
        "conversation_id": conversation_id,
    }
    if mode:
        payload["mode"] = mode

    first = send_request(client, url, payload)
    retried_without_mode = False
    if mode and first["http_status"] in {400, 422}:
        retry_payload = {key: value for key, value in payload.items() if key != "mode"}
        second = send_request(client, url, retry_payload)
        if second["http_status"] and second["http_status"] < 500:
            first = second
            retried_without_mode = True

    first.update(
        {
            "case_id": case.case_id,
            "question": case.question,
            "payload": first.get("payload", payload),
            "retried_without_mode": retried_without_mode,
        }
    )
    return first


def send_request(
    client: httpx.Client,
    url: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = client.post(url, json=payload)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "http_status": response.status_code,
            "elapsed_ms": elapsed_ms,
            "payload": payload,
            "response_json": safe_json(response),
            "response_text": response.text,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - diagnostic runner
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "http_status": None,
            "elapsed_ms": elapsed_ms,
            "payload": payload,
            "response_json": None,
            "response_text": "",
            "error": repr(exc),
        }


def evaluate_record(case: EvaluationCase, record: dict[str, Any]) -> ScoreBreakdown:
    issues: list[str] = []
    body = record.get("response_json")
    answer = body.get("answer", "") if isinstance(body, dict) else ""
    sources = body.get("sources", []) if isinstance(body, dict) else []
    reasoning = body.get("reasoning", []) if isinstance(body, dict) else []
    tool_calls = body.get("tool_calls", []) if isinstance(body, dict) else []
    status = body.get("status") if isinstance(body, dict) else None

    technical = technical_score(record, body, answer, sources, reasoning, status, issues)
    functional = functional_score(case, answer, sources, tool_calls, issues, technical)
    quality = information_quality_score(case, answer, issues, technical)
    traceability = traceability_score(case, sources, reasoning, tool_calls, body, issues, technical)
    human = human_wording_score(case, answer, issues, technical)

    score = ScoreBreakdown(
        functional=functional,
        information_quality=quality,
        traceability=traceability,
        human_wording=human,
        technical_robustness=technical,
        issues=issues,
    )
    if fatal_contract_issue(body, answer, sources, reasoning):
        issues.append("Fallo grave de contrato: faltan answer, sources o reasoning utiles.")
        cap_score(score, 7)
    elif not expected_sources_covered(case, sources):
        issues.append(
            "Fuentes incompletas para la pregunta: esperadas "
            f"{', '.join(case.expected_sources)}; recibidas {', '.join(map(str, sources)) or 'ninguna'}."
        )
        cap_score(score, 17)
    return score


def technical_score(
    record: dict[str, Any],
    body: Any,
    answer: Any,
    sources: Any,
    reasoning: Any,
    status: Any,
    issues: list[str],
) -> int:
    score = 0
    if record.get("http_status") == 200:
        score += 1
    else:
        issues.append(f"HTTP no exitoso: {record.get('http_status')} {record.get('error') or ''}".strip())
    if isinstance(body, dict):
        score += 1
    else:
        issues.append("La respuesta no es un objeto JSON valido.")
    if isinstance(answer, str) and isinstance(sources, list) and isinstance(reasoning, list):
        score += 1
    else:
        issues.append("Tipos invalidos en answer/sources/reasoning.")
    if sources and reasoning:
        score += 1
    else:
        issues.append("sources o reasoning vienen vacios.")
    if status not in {"failed", "tool_error"} and not record.get("error"):
        score += 1
    else:
        issues.append(f"Estado tecnico problematico: {status or record.get('error')}.")
    return score


def functional_score(
    case: EvaluationCase,
    answer: str,
    sources: list[Any],
    tool_calls: list[Any],
    issues: list[str],
    technical: int,
) -> int:
    if technical == 0:
        return 0
    normalized_answer = normalize_text(answer)
    source_score = source_coverage_score(case.expected_sources, sources)
    required_hit = all(normalize_text(term) in normalized_answer for term in case.required_terms)
    any_hits = sum(
        1
        for group in case.required_any_terms
        if any(normalize_text(term) in normalized_answer for term in group)
    )
    tools_text = normalize_text(json.dumps(tool_calls, ensure_ascii=False))

    score = 1 if answer.strip() else 0
    score += min(2, source_score)
    if required_hit:
        score += 1
    else:
        issues.append(f"No aparecen todos los datos obligatorios: {', '.join(case.required_terms) or 'n/a'}.")
    if not case.required_any_terms or any_hits == len(case.required_any_terms):
        score += 1
    elif any_hits:
        issues.append("Solo se cumplen parcialmente los terminos funcionales esperados.")
    else:
        issues.append("No se observan evidencias funcionales clave en la respuesta.")

    if "documentos" in normalize_sources(case.expected_sources):
        if "documentragtool" not in tools_text and "documentos" not in normalize_sources(sources):
            score = max(0, score - 1)
            issues.append("No se aprecia uso real de RAG/documentos.")
    if {"erp", "produccion"}.issubset(set(normalize_sources(case.expected_sources))):
        actual = set(normalize_sources(sources))
        if not {"erp", "produccion"}.issubset(actual):
            score = max(0, score - 1)
            issues.append("No se aprecia integracion ERP + Produccion completa.")
    return min(score, 5)


def information_quality_score(
    case: EvaluationCase,
    answer: str,
    issues: list[str],
    technical: int,
) -> int:
    if technical == 0:
        return 0
    normalized = normalize_text(answer)
    score = 0
    if len(answer.strip()) >= 60:
        score += 1
    else:
        issues.append("Respuesta demasiado corta para ser util.")
    if re.search(r"\b10\d{3}\b|\b\d+[,.]?\d*\s*(eur|€|%)|\b2026[-/]\d{2}", normalized):
        score += 1
    elif "documentos" in normalize_sources(case.expected_sources) and any(
        term in normalized for term in ("5 dias", "cinco dias", "48 horas", "2%", "5%")
    ):
        score += 1
    else:
        issues.append("Faltan datos concretos: pedidos, importes, fechas, porcentajes o plazos.")
    required_hits = sum(1 for term in case.required_terms if normalize_text(term) in normalized)
    any_group_hits = sum(
        1
        for group in case.required_any_terms
        if any(normalize_text(term) in normalized for term in group)
    )
    if required_hits == len(case.required_terms):
        score += 1
    if not case.required_any_terms or any_group_hits == len(case.required_any_terms):
        score += 1
    elif any_group_hits:
        issues.append("La informacion concreta esperada aparece solo de forma parcial.")
    vague_terms = ("no tengo informacion", "no hay datos", "no puedo determinar", "informacion no disponible")
    if not any(term in normalized for term in vague_terms):
        score += 1
    else:
        issues.append("La respuesta suena vaga o no aprovecha datos esperados.")
    return min(score, 5)


def traceability_score(
    case: EvaluationCase,
    sources: list[Any],
    reasoning: list[Any],
    tool_calls: list[Any],
    body: Any,
    issues: list[str],
    technical: int,
) -> int:
    if technical == 0:
        return 0
    score = 0
    if sources:
        score += 1
    if expected_sources_covered(case, sources):
        score += 1
    if reasoning:
        score += 1
    reasoning_text = normalize_text(" ".join(str(item) for item in reasoning))
    generic_reasoning = all(
        term not in reasoning_text
        for term in (
            "erp",
            "produccion",
            "document",
            "rag",
            "pedido",
            "cliente",
            "bloque",
            "traz",
            "memoria",
        )
    )
    if reasoning and not generic_reasoning:
        score += 1
    else:
        issues.append("reasoning demasiado generico o poco auditable.")
    if len(reasoning) == 1 and len(str(reasoning[0])) < 80:
        score = max(0, score - 1)
        issues.append("reasoning minimo: explica la fuente, pero no desarrolla pasos/lógica con suficiente detalle.")
    if tool_calls or (isinstance(body, dict) and body.get("data")):
        score += 1
    else:
        issues.append("No hay tool_calls ni data publica para auditar pasos.")
    return min(score, 5)


def human_wording_score(
    case: EvaluationCase,
    answer: str,
    issues: list[str],
    technical: int,
) -> int:
    if technical == 0:
        return 0
    normalized = normalize_text(answer)
    score = 0
    if 60 <= len(answer.strip()) <= 2500:
        score += 1
    else:
        issues.append("Longitud poco adecuada para usuario de negocio.")
    forbidden = [
        term
        for term in case.forbidden_answer_terms
        if normalize_text(term) in normalized or term in answer
    ]
    if not forbidden:
        score += 1
    else:
        issues.append("La respuesta contiene restos de chunk/JSON/metadatos: " + ", ".join(forbidden))
    if "{" not in answer[:80] and "}" not in answer[-80:]:
        score += 1
    else:
        issues.append("La respuesta parece JSON crudo en lugar de redaccion final.")
    if re.search(r"[.!?:]\s", answer.strip()) or "\n-" in answer or "\n*" in answer:
        score += 1
    else:
        issues.append("Redaccion poco natural o sin estructura legible.")
    robotic_terms = ("segun la evidencia actual", "respuesta generada", "fuera del alcance de esta poc")
    if not any(term in normalized for term in robotic_terms):
        score += 1
    else:
        issues.append("Tono demasiado robotico o propio de una PoC.")
    return min(score, 5)


def fatal_contract_issue(body: Any, answer: Any, sources: Any, reasoning: Any) -> bool:
    return not (
        isinstance(body, dict)
        and isinstance(answer, str)
        and answer.strip()
        and isinstance(sources, list)
        and len(sources) > 0
        and isinstance(reasoning, list)
        and len(reasoning) > 0
    )


def cap_score(score: ScoreBreakdown, maximum: int) -> None:
    while score.total > maximum:
        if score.functional > 0:
            score.functional -= 1
        elif score.information_quality > 0:
            score.information_quality -= 1
        elif score.traceability > 0:
            score.traceability -= 1
        elif score.human_wording > 0:
            score.human_wording -= 1
        elif score.technical_robustness > 0:
            score.technical_robustness -= 1
        else:
            break


def expected_sources_covered(case: EvaluationCase, sources: list[Any]) -> bool:
    return set(normalize_sources(case.expected_sources)).issubset(set(normalize_sources(sources)))


def source_coverage_score(expected: tuple[str, ...], actual: list[Any]) -> int:
    expected_set = set(normalize_sources(expected))
    actual_set = set(normalize_sources(actual))
    if not expected_set:
        return 2
    hits = len(expected_set & actual_set)
    if hits == len(expected_set):
        return 2
    if hits:
        return 1
    return 0


def normalize_sources(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    return [normalize_text(str(value)).replace("produccion", "produccion") for value in values]


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value))
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.lower()


def verdict_for(score: int) -> str:
    if score >= 22:
        return "Excelente, nivel entrega solida"
    if score >= 18:
        return "Aceptable, pero mejorable"
    if score >= 14:
        return "Riesgo medio"
    if score >= 8:
        return "Riesgo alto"
    return "Fallo grave"


def average_score(evaluations: list[dict[str, Any]]) -> float:
    if not evaluations:
        return 0.0
    return sum(item["score"].total for item in evaluations) / len(evaluations)


def global_verdict(evaluations: list[dict[str, Any]], health: dict[str, Any]) -> str:
    if not health["ok"]:
        return "Fallo grave: la API no levanta correctamente en Docker."
    avg = average_score(evaluations)
    severe = [item for item in evaluations if item["score"].total < 14]
    if severe:
        return "Riesgo alto: hay respuestas por debajo del umbral minimo de entrega."
    if avg >= 22:
        return "Excelente: entrega solida para evaluacion tecnica."
    if avg >= 18:
        return "Aceptable: cumple, con mejoras recomendadas."
    if avg >= 14:
        return "Riesgo medio: hay carencias relevantes antes de entregar."
    return "Fallo grave: no alcanza los minimos funcionales."


def render_report(
    *,
    generated_at: str,
    docker_command: str,
    base_url: str,
    endpoint: str,
    mode: str,
    health: dict[str, Any],
    evaluations: list[dict[str, Any]],
    raw_output: Path,
    compose_config_path: Path,
) -> str:
    avg = average_score(evaluations)
    risks = main_risks(evaluations, health)
    improvements = priority_improvements(evaluations, health)
    lines: list[str] = [
        "# Evaluación automática Docker/API",
        "",
        "## Configuración",
        f"- Fecha: {generated_at}",
        f"- Comando Docker usado: `{docker_command}`",
        f"- Base URL: `{base_url}`",
        f"- Endpoint: `{endpoint}`",
        f"- Mode: `{mode}`",
        "- Servicios Docker levantados: `backend`, `production-api`, `chromadb` y servicio `evaluator` con profile `eval`; `chainlit` no se usa en esta evaluación.",
        f"- Total preguntas: {len(evaluations)}",
        f"- Respuestas crudas: `{raw_output.as_posix()}`",
        "",
        "## Resumen ejecutivo",
        f"- Puntuación media: {avg:.1f}/25",
        f"- Veredicto global: {global_verdict(evaluations, health)}",
        "- Riesgos principales:",
        *[f"  - {risk}" for risk in risks],
        "- Mejoras prioritarias:",
        *[f"  - {improvement}" for improvement in improvements],
        "",
        "## Estado Docker",
        f"- Resultado de docker compose config: {compose_config_summary(compose_config_path)}",
        f"- Resultado de healthcheck: {healthcheck_summary(health)}",
        f"- Errores relevantes de logs si existen: {error_summary(evaluations, health)}",
        "",
        "## Tabla resumen",
        "| ID | Pregunta | HTTP | Score | Veredicto breve |",
        "|----|----------|------|-------|-----------------|",
    ]
    for item in evaluations:
        case = item["case"]
        record = item["record"]
        score = item["score"]
        question = case.question.replace("|", "\\|")
        lines.append(
            f"| {case.case_id} | {question} | {record.get('http_status') or 'ERROR'} | "
            f"{score.total}/25 | {verdict_for(score.total)} |"
        )

    lines.extend(["", "## Evaluación detallada", ""])
    for item in evaluations:
        lines.extend(render_case_detail(item))
    return "\n".join(lines).rstrip() + "\n"


def render_case_detail(item: dict[str, Any]) -> list[str]:
    case: EvaluationCase = item["case"]
    record: dict[str, Any] = item["record"]
    score: ScoreBreakdown = item["score"]
    body = record.get("response_json") if isinstance(record.get("response_json"), dict) else {}
    answer = body.get("answer", "") if isinstance(body, dict) else ""
    sources = body.get("sources", []) if isinstance(body, dict) else []
    reasoning = body.get("reasoning", []) if isinstance(body, dict) else []
    payload = record.get("payload", {})
    response_excerpt = answer.strip()[:1200] or record.get("response_text", "")[:1200]
    issues = score.issues or ["Sin problemas graves detectados por heuristica."]
    return [
        f"### Pregunta {case.case_id}",
        "**Pregunta enviada:**",
        "",
        case.question,
        "",
        "**Payload:**",
        "",
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=2),
        "```",
        "",
        "**Respuesta visible para usuario (extracto):**",
        "",
        response_excerpt,
        "",
        "**Fuentes devueltas:**",
        "",
        ", ".join(map(str, sources)) or "Ninguna",
        "",
        "**Reasoning devuelto:**",
        "",
        "\n".join(f"- {item}" for item in reasoning) or "Ninguno",
        "",
        "**Puntuación:**",
        "",
        (
            f"- Cumplimiento funcional: {score.functional}/5\n"
            f"- Calidad de información: {score.information_quality}/5\n"
            f"- Trazabilidad: {score.traceability}/5\n"
            f"- Redacción humana: {score.human_wording}/5\n"
            f"- Robustez técnica: {score.technical_robustness}/5\n"
            f"- Total: {score.total}/25 ({verdict_for(score.total)})"
        ),
        "",
        "**Problemas detectados:**",
        "",
        *[f"- {issue}" for issue in issues],
        "",
        "**Criterio esperado por evaluador:**",
        "",
        case.expected_behavior,
        "",
    ]


def main_risks(evaluations: list[dict[str, Any]], health: dict[str, Any]) -> list[str]:
    if not health["ok"]:
        return ["La API no respondio al healthcheck en Docker."]
    risks: list[str] = []
    for item in evaluations:
        score: ScoreBreakdown = item["score"]
        case: EvaluationCase = item["case"]
        if score.total < 18:
            risks.append(f"Pregunta {case.case_id}: {verdict_for(score.total)} ({score.total}/25).")
    if not risks and any(item["score"].total < 25 for item in evaluations):
        weakest = sorted(evaluations, key=lambda item: item["score"].total)[:3]
        risks = [
            f"Pregunta {item['case'].case_id}: punto mas debil relativo con {item['score'].total}/25."
            for item in weakest
        ]
    return risks[:5] or ["No hay riesgos bloqueantes en las preguntas evaluadas; queda revision manual de casos limite."]


def priority_improvements(evaluations: list[dict[str, Any]], health: dict[str, Any]) -> list[str]:
    if not health["ok"]:
        return ["Corregir arranque Docker/healthcheck antes de evaluar funcionalidad."]
    improvements: list[str] = []
    all_issues = " ".join(
        issue.lower()
        for item in evaluations
        for issue in item["score"].issues
    )
    if "reasoning minimo" in all_issues:
        improvements.append(
            "Ampliar el reasoning de respuestas RAG para explicar pasos y logica, no solo la fuente consultada."
        )
    if "terminos funcionales" in all_issues or "informacion concreta" in all_issues:
        improvements.append(
            "Revisar prompts/casos RAG para cubrir todos los conceptos esperados en contrato y penalizaciones."
        )
    for label, attr in (
        ("Refinar integracion funcional de fuentes", "functional"),
        ("Aumentar datos concretos en respuestas", "information_quality"),
        ("Hacer reasoning y tool_calls mas auditables", "traceability"),
        ("Mejorar redaccion final humana", "human_wording"),
        ("Endurecer contrato JSON/errores", "technical_robustness"),
    ):
        average = sum(getattr(item["score"], attr) for item in evaluations) / len(evaluations)
        if average < 4:
            improvements.append(f"{label} (media {average:.1f}/5).")
    return improvements[:5] or ["Mantener la cobertura actual y revisar manualmente las preguntas de borde."]


def compose_config_summary(path: Path) -> str:
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        if text.strip():
            return f"OK: salida disponible en `{path.as_posix()}` ({len(text.splitlines())} lineas)."
    compose_file = Path("docker-compose.yml")
    if compose_file.exists():
        text = compose_file.read_text(encoding="utf-8", errors="replace")
        checks = {
            "backend healthcheck": "healthcheck:" in text and "backend:" in text,
            "AGENT_MODE deepagent": "AGENT_MODE: ${AGENT_MODE:-deepagent}" in text,
            "evaluator profile eval": "evaluator:" in text and "profiles:" in text and "eval" in text,
        }
        failed = [name for name, ok in checks.items() if not ok]
        if not failed:
            return "OK: compose inspeccionado; backend tiene healthcheck, AGENT_MODE default deepagent y evaluator profile eval."
        return "Riesgo: compose inspeccionado con faltantes: " + ", ".join(failed) + "."
    return "No disponible dentro del contenedor evaluator; generar con `docker compose config > reports/docker_compose_config.txt`."


def healthcheck_summary(health: dict[str, Any]) -> str:
    if health["ok"]:
        return f"OK HTTP {health['http_status']} en {health['url']} tras {health['attempts']} intento(s)."
    return f"FAIL en {health['url']}: {health.get('error') or 'timeout'}."


def error_summary(evaluations: list[dict[str, Any]], health: dict[str, Any]) -> str:
    errors: list[str] = []
    if not health["ok"]:
        errors.append(str(health.get("error") or "healthcheck fallido"))
    for item in evaluations:
        record = item["record"]
        if record.get("http_status") and int(record["http_status"]) >= 400:
            errors.append(
                f"Pregunta {item['case'].case_id}: HTTP {record['http_status']} "
                f"{str(record.get('response_text') or '')[:180]}"
            )
        elif record.get("error"):
            errors.append(f"Pregunta {item['case'].case_id}: {record['error']}")
    return " | ".join(errors[:5]) if errors else "No se detectan errores HTTP/logicos graves en la ejecucion HTTP."


def safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def safe_json_or_text(response: httpx.Response) -> Any:
    parsed = safe_json(response)
    if parsed is not None:
        return parsed
    return response.text[:500]


def join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


if __name__ == "__main__":
    raise SystemExit(main())
