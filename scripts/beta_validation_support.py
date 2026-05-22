from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.schemas.query import QueryResponse
from chainlit_app.formatting import format_query_response


ROBOTIC_PUBLIC_PHRASES = (
    "sin inventar",
    "pregunta fuera del alcance",
    "fuera del alcance de esta poc",
    "no hay contexto suficiente",
    "evidencia actual",
    "exclusion documental",
)


@dataclass(frozen=True)
class BetaExpectation:
    status: str
    sources: tuple[str, ...] | None = None
    required_tools: tuple[str, ...] = ()
    required_answer_terms: tuple[str, ...] = ()
    required_any_answer_terms: tuple[tuple[str, ...], ...] = ()
    forbidden_answer_terms: tuple[str, ...] = ROBOTIC_PUBLIC_PHRASES
    required_data_values: dict[str, Any] = field(default_factory=dict)
    required_data_contains: dict[str, tuple[Any, ...]] = field(default_factory=dict)
    required_rag_documents: tuple[str, ...] = ()
    min_rag_chunks: int | None = None
    allow_llm_fallbacks: bool = False


@dataclass(frozen=True)
class BetaTurn:
    question: str
    expectation: BetaExpectation


@dataclass(frozen=True)
class BetaCase:
    case_id: str
    title: str
    evaluator_expected: str
    turns: tuple[BetaTurn, ...]


@dataclass(frozen=True)
class BetaTurnVerdict:
    status: str
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class BetaCaseVerdict:
    status: str
    turn_verdicts: tuple[BetaTurnVerdict, ...]

    @property
    def issues(self) -> tuple[str, ...]:
        return tuple(
            issue
            for verdict in self.turn_verdicts
            for issue in verdict.issues
        )


OBLIGATORY_BETA_CASES: tuple[BetaCase, ...] = (
    BetaCase(
        case_id="BT-01",
        title="ERP + produccion: pendientes ALFKI",
        evaluator_expected=(
            "Debe listar pedidos pendientes de ALFKI y sus estados de produccion."
        ),
        turns=(
            BetaTurn(
                question=(
                    "Que pedidos pendientes tiene el cliente ALFKI y en que estado "
                    "de produccion estan?"
                ),
                expectation=BetaExpectation(
                    status="completed",
                    sources=("ERP", "Produccion"),
                    required_tools=("ERPTool", "ProductionAPITool"),
                    required_answer_terms=("10248", "10252"),
                    required_any_answer_terms=(("ALFKI", "Alfreds Futterkiste"),),
                    required_data_contains={
                        "erp_order_ids": (10248, 10252),
                    },
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-02",
        title="ERP + produccion: bloqueos",
        evaluator_expected=(
            "Debe listar pedidos bloqueados y motivo, cruzando produccion con ERP."
        ),
        turns=(
            BetaTurn(
                question="Que pedidos estan bloqueados y cual es el motivo?",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Produccion", "ERP"),
                    required_tools=("ProductionAPITool", "ERPTool"),
                    required_answer_terms=(
                        "10252",
                        "10312",
                        "Falta de material",
                        "Falta de capacidad",
                    ),
                    required_data_contains={
                        "production_order_ids": (10252, 10312),
                    },
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-03",
        title="ERP + produccion: retrasos",
        evaluator_expected=(
            "Debe identificar pedidos delayed y cliente ERP asociado."
        ),
        turns=(
            BetaTurn(
                question=(
                    "Que clientes tienen pedidos retrasados por problemas de "
                    "produccion?"
                ),
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Produccion", "ERP"),
                    required_tools=("ProductionAPITool", "ERPTool"),
                    required_answer_terms=("10301",),
                    required_any_answer_terms=(
                        ("ANATR", "Ana Trujillo"),
                        ("Averia", "averia", "retrasado"),
                    ),
                    required_data_contains={
                        "production_order_ids": (10301,),
                    },
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-04",
        title="ERP + produccion: resumen mensual",
        evaluator_expected=(
            "Debe resumir pedidos de mayo de 2026 y su distribucion de estados."
        ),
        turns=(
            BetaTurn(
                question="Dame un resumen del estado de los pedidos de este mes",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("ERP", "Produccion"),
                    required_tools=("ERPTool", "ProductionAPITool"),
                    required_answer_terms=("5",),
                    required_any_answer_terms=(
                        ("2026-05", "mayo", "mes"),
                        ("bloqueado", "bloqueados"),
                        ("retrasado", "retrasados"),
                    ),
                    required_data_values={
                        "period.year": 2026,
                        "period.month": 5,
                    },
                    required_data_contains={
                        "erp_order_ids": (10248, 10252, 10255, 10301, 10312),
                    },
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-05",
        title="RAG: plazos de entrega",
        evaluator_expected=(
            "Debe recuperar reglas documentales de plazos de entrega."
        ),
        turns=(
            BetaTurn(
                question="Que dice el documento sobre plazos de entrega standard?",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    required_any_answer_terms=(
                        ("5 dias laborables", "5 dias", "cinco dias"),
                    ),
                    required_rag_documents=(
                        "v2_contrato_marco_logistica_2026.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-06",
        title="RAG: resumen del contrato",
        evaluator_expected="Debe resumir contrato con citas documentales.",
        turns=(
            BetaTurn(
                question="Resume los puntos clave del contrato",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    required_any_answer_terms=(
                        ("contrato", "logistica"),
                        ("entrega", "expedicion", "plazos"),
                    ),
                    required_rag_documents=(
                        "v2_contrato_marco_logistica_2026.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-07",
        title="RAG: penalizaciones",
        evaluator_expected=(
            "Debe responder sobre penalizaciones usando anexo SLA o contrato."
        ),
        turns=(
            BetaTurn(
                question="Segun el PDF, hay alguna penalizacion por retrasos?",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    required_answer_terms=("penaliz",),
                    required_rag_documents=(
                        "v2_anexo_penalizaciones_sla.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-08",
        title="Mixta: penalizaciones por pedido",
        evaluator_expected=(
            "Debe combinar pedidos ERP, estado de produccion y reglas documentales."
        ),
        turns=(
            BetaTurn(
                question=(
                    "en funcion de los pedidos y su estado dime que penalizaciones "
                    "vamos a tener en cada uno"
                ),
                expectation=BetaExpectation(
                    status="completed",
                    sources=("ERP", "Produccion", "Documentos"),
                    required_tools=(
                        "ERPTool",
                        "ProductionAPITool",
                        "DocumentRAGTool",
                    ),
                    required_answer_terms=(
                        "10248",
                        "10252",
                        "10255",
                        "10301",
                        "10312",
                    ),
                    required_rag_documents=(
                        "v2_anexo_penalizaciones_sla.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-09",
        title="Memoria conversacional",
        evaluator_expected=(
            "Debe resolver referencias conversacionales sin usar memoria como "
            "fuente de verdad de negocio."
        ),
        turns=(
            BetaTurn(
                question="Que pedidos pendientes tiene el cliente ALFKI?",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("ERP",),
                    required_tools=("ERPTool",),
                    required_answer_terms=("10248", "10252"),
                    required_data_contains={
                        "erp_order_ids": (10248, 10252),
                    },
                ),
            ),
            BetaTurn(
                question="Y cuales de esos pedidos estan bloqueados?",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Memoria", "Produccion", "ERP"),
                    required_tools=("MemoryTool", "ProductionAPITool", "ERPTool"),
                    required_answer_terms=("10252", "Falta de material"),
                    required_data_contains={
                        "production_order_ids": (10252,),
                    },
                ),
            ),
            BetaTurn(
                question="Cual es el impacto economico de esos?",
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Memoria", "ERP"),
                    required_tools=("MemoryTool", "ERPTool"),
                    required_answer_terms=("10252", "1863.00"),
                    required_data_values={
                        "economic_impact_total": "1863.00",
                    },
                    required_data_contains={
                        "order_amount_order_ids": (10252,),
                    },
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-10",
        title="Guardrail RAG",
        evaluator_expected=(
            "Debe rechazar por contexto documental insuficiente y no inventar."
        ),
        turns=(
            BetaTurn(
                question="Segun el PDF, que receta de cocina vegana recomienda?",
                expectation=BetaExpectation(
                    status="insufficient_context",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    forbidden_answer_terms=ROBOTIC_PUBLIC_PHRASES
                    + ("recomiendo", "ingredientes", "preparacion"),
                    required_data_values={
                        "rag.chunks_count": 0,
                    },
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-11",
        title="Memoria aislada",
        evaluator_expected=(
            "Debe aislar conversaciones por conversation_id y pedir contexto previo."
        ),
        turns=(
            BetaTurn(
                question="Y en que estado estan?",
                expectation=BetaExpectation(
                    status="needs_clarification",
                    sources=(),
                    required_tools=(),
                    required_any_answer_terms=(
                        ("cliente", "pedido", "periodo", "contexto"),
                    ),
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-V2-01",
        title="V2: hitos y evidencias minimas",
        evaluator_expected=(
            "Debe recuperar el contrato v2 y citar la pagina donde estan los "
            "hitos y evidencias minimas."
        ),
        turns=(
            BetaTurn(
                question=(
                    "Segun v2_contrato_marco_logistica_2026.pdf, que hitos "
                    "obligatorios debe conservar cada expedicion?"
                ),
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    required_any_answer_terms=(("hitos", "evidencias"),),
                    required_rag_documents=(
                        "v2_contrato_marco_logistica_2026.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-V2-02",
        title="V2: evidencia SLA",
        evaluator_expected=(
            "Debe recuperar el anexo v2 y explicar evidencia obligatoria y carga "
            "de la prueba."
        ),
        turns=(
            BetaTurn(
                question=(
                    "Segun v2_anexo_penalizaciones_sla.pdf, que evidencia es "
                    "obligatoria y que pasa si no se puede demostrar la causa del "
                    "retraso?"
                ),
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    required_any_answer_terms=(
                        ("order_id", "customer_id", "causa"),
                        ("evidencia", "responsabilidad"),
                    ),
                    required_rag_documents=(
                        "v2_anexo_penalizaciones_sla.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-V2-03",
        title="V2: exclusiones y pausas SLA",
        evaluator_expected=(
            "Debe recuperar el anexo v2 y explicar exclusiones, pausas y casos no "
            "penalizables."
        ),
        turns=(
            BetaTurn(
                question=(
                    "Segun v2_anexo_penalizaciones_sla.pdf, que exclusiones y "
                    "pausas de SLA existen?"
                ),
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    required_any_answer_terms=(
                        ("bloqueo", "falta de material", "capacidad"),
                        ("pausa", "SLA"),
                    ),
                    required_rag_documents=(
                        "v2_anexo_penalizaciones_sla.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-V2-04",
        title="V2: bloqueos de produccion",
        evaluator_expected=(
            "Debe recuperar el procedimiento v2 y explicar motivos/campos de "
            "bloqueo."
        ),
        turns=(
            BetaTurn(
                question=(
                    "Segun v2_procedimiento_produccion_bloqueos.pdf, que motivos "
                    "de bloqueo y campos obligatorios se registran?"
                ),
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    required_any_answer_terms=(
                        ("falta de material", "falta de capacidad"),
                        ("order_id", "responsable", "impacto"),
                    ),
                    required_rag_documents=(
                        "v2_procedimiento_produccion_bloqueos.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-V2-05",
        title="V2: calidad y entregas parciales",
        evaluator_expected=(
            "Debe recuperar politica de calidad v2 y explicar control previo e "
            "incidencias."
        ),
        turns=(
            BetaTurn(
                question=(
                    "Segun v2_politica_calidad_entregas.pdf, que ocurre con "
                    "incidencias de calidad y entregas parciales?"
                ),
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    required_any_answer_terms=(
                        ("calidad", "lote"),
                        ("entregas parciales", "parciales"),
                    ),
                    required_rag_documents=(
                        "v2_politica_calidad_entregas.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-V2-06",
        title="V2: impacto economico y trazabilidad",
        evaluator_expected=(
            "Debe recuperar condiciones comerciales v2 y explicar impacto "
            "economico/trazabilidad."
        ),
        turns=(
            BetaTurn(
                question=(
                    "Segun v2_condiciones_comerciales_northwind.pdf, como se "
                    "calcula el impacto economico y que trazabilidad se exige?"
                ),
                expectation=BetaExpectation(
                    status="completed",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    required_any_answer_terms=(
                        ("impacto economico", "importe"),
                        ("trazabilidad", "pedido"),
                    ),
                    required_rag_documents=(
                        "v2_condiciones_comerciales_northwind.pdf",
                    ),
                    min_rag_chunks=1,
                ),
            ),
        ),
    ),
    BetaCase(
        case_id="BT-V2-07",
        title="V2: guardrail documental multipagina",
        evaluator_expected=(
            "Debe rechazar por contexto documental insuficiente y no inventar."
        ),
        turns=(
            BetaTurn(
                question=(
                    "Segun los documentos v2, que receta de cocina vegana "
                    "recomienda para un cliente premium?"
                ),
                expectation=BetaExpectation(
                    status="insufficient_context",
                    sources=("Documentos",),
                    required_tools=("DocumentRAGTool",),
                    forbidden_answer_terms=ROBOTIC_PUBLIC_PHRASES
                    + ("recomiendo", "ingredientes", "preparacion"),
                    required_data_values={
                        "rag.chunks_count": 0,
                    },
                ),
            ),
        ),
    ),
)


def evaluate_beta_case(
    beta_case: BetaCase,
    responses: list[QueryResponse],
) -> BetaCaseVerdict:
    if len(responses) != len(beta_case.turns):
        return BetaCaseVerdict(
            status="BLOCKER",
            turn_verdicts=(
                BetaTurnVerdict(
                    status="BLOCKER",
                    issues=(
                        "numero de respuestas distinto al numero de turnos "
                        f"({len(responses)} != {len(beta_case.turns)})",
                    ),
                ),
            ),
        )

    turn_verdicts = tuple(
        evaluate_beta_turn(turn, response)
        for turn, response in zip(beta_case.turns, responses, strict=True)
    )
    if any(verdict.status == "FAIL" for verdict in turn_verdicts):
        status = "FAIL"
    elif any(verdict.status == "PARTIAL" for verdict in turn_verdicts):
        status = "PARTIAL"
    else:
        status = "PASS"
    return BetaCaseVerdict(status=status, turn_verdicts=turn_verdicts)


def evaluate_beta_turn(turn: BetaTurn, response: QueryResponse) -> BetaTurnVerdict:
    expected = turn.expectation
    issues: list[str] = []

    if response.status != expected.status:
        issues.append(f"status esperado {expected.status!r}, recibido {response.status!r}")

    if expected.sources is not None and tuple(response.sources) != expected.sources:
        issues.append(
            f"sources esperadas {list(expected.sources)!r}, recibidas {response.sources!r}"
        )

    actual_tools = [call.tool for call in response.tool_calls]
    for tool in expected.required_tools:
        if tool not in actual_tools:
            issues.append(f"tool obligatoria ausente: {tool}")

    normalized_answer = _normalize_text(response.answer)
    for term in expected.required_answer_terms:
        if _normalize_text(term) not in normalized_answer:
            issues.append(f"termino obligatorio ausente en answer: {term!r}")

    for group in expected.required_any_answer_terms:
        if not any(_normalize_text(term) in normalized_answer for term in group):
            issues.append(
                "ningun termino alternativo aparece en answer: "
                + ", ".join(repr(term) for term in group)
            )

    for term in expected.forbidden_answer_terms:
        if _normalize_text(term) in normalized_answer:
            issues.append(f"termino prohibido en answer: {term!r}")

    data = response.data or {}
    for path, expected_value in expected.required_data_values.items():
        actual_value = _value_at_path(data, path)
        if actual_value != expected_value:
            issues.append(
                f"data.{path} esperado {expected_value!r}, recibido {actual_value!r}"
            )

    for path, required_items in expected.required_data_contains.items():
        actual_value = _value_at_path(data, path)
        if not isinstance(actual_value, list):
            issues.append(f"data.{path} no es lista: {actual_value!r}")
            continue
        missing = [item for item in required_items if item not in actual_value]
        if missing:
            issues.append(f"data.{path} no contiene {missing!r}")

    rag = data.get("rag") if isinstance(data, dict) else None
    if expected.required_rag_documents:
        documents = rag.get("documents") if isinstance(rag, dict) else None
        if not isinstance(documents, list):
            issues.append("data.rag.documents ausente o no es lista")
        else:
            missing_docs = [
                document
                for document in expected.required_rag_documents
                if document not in documents
            ]
            if missing_docs:
                issues.append(f"documentos RAG obligatorios ausentes: {missing_docs!r}")

    if expected.min_rag_chunks is not None:
        chunks_count = rag.get("chunks_count") if isinstance(rag, dict) else None
        if not isinstance(chunks_count, int) or chunks_count < expected.min_rag_chunks:
            issues.append(
                "chunks RAG insuficientes: "
                f"esperado >= {expected.min_rag_chunks}, recibido {chunks_count!r}"
            )

    fallback_issues = _unexpected_llm_fallbacks(response, expected)
    issues.extend(fallback_issues)

    status = "PASS" if not issues else "FAIL"
    return BetaTurnVerdict(status=status, issues=tuple(issues))


def render_beta_case_report(
    beta_case: BetaCase,
    responses: list[QueryResponse],
    verdict: BetaCaseVerdict,
) -> str:
    lines = [
        f"### {beta_case.case_id} - {verdict.status} - {beta_case.title}",
        "",
    ]
    for index, (turn, response) in enumerate(
        zip(beta_case.turns, responses, strict=True),
        start=1,
    ):
        prefix = "Pregunta ejecutada" if len(beta_case.turns) == 1 else f"Turno {index}"
        lines.extend(
            [
                f"{prefix}: `{turn.question}`",
                "",
                f"Resultado esperado desde el evaluador: {beta_case.evaluator_expected}",
                "",
                "Respuesta exacta visible en Chainlit:",
                "",
                "```markdown",
                format_query_response(response),
                "```",
                "",
                "Evidencia tecnica resumida:",
                "",
                "```json",
                json.dumps(
                    _technical_summary(response),
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
            ]
        )

    if verdict.issues:
        lines.append("Incidencias detectadas:")
        lines.extend(f"- {issue}" for issue in verdict.issues)
        lines.append("")

    lines.extend(
        [
            f"Veredicto: `{verdict.status}`",
            "",
        ]
    )
    return "\n".join(lines)


def _unexpected_llm_fallbacks(
    response: QueryResponse,
    expected: BetaExpectation,
) -> list[str]:
    issues = _unexpected_rag_infra_fallbacks(response)
    if expected.allow_llm_fallbacks:
        return issues
    unexpected = [
        fallback
        for fallback in response.fallbacks
        if fallback.startswith(
            (
                "FALLBACK_PLANNER_RULE_BASED",
                "FALLBACK_FINAL_RESPONSE_DETERMINISTIC",
            )
        )
    ]
    issues.extend(f"fallback LLM inesperado: {fallback}" for fallback in unexpected)
    return issues


def _unexpected_rag_infra_fallbacks(response: QueryResponse) -> list[str]:
    forbidden_prefixes = (
        "FALLBACK_VECTOR_STORE_IN_MEMORY",
        "FALLBACK_EMBEDDINGS_DETERMINISTIC",
    )
    fallback_candidates = list(response.fallbacks)
    for call in response.tool_calls:
        if call.output_summary:
            fallback_candidates.append(call.output_summary)

    rag = response.data.get("rag") if isinstance(response.data, dict) else None
    if isinstance(rag, dict):
        fallback_candidates.extend(str(value) for value in rag.get("fallbacks", []))

    unexpected = [
        fallback
        for fallback in fallback_candidates
        if any(prefix in fallback for prefix in forbidden_prefixes)
    ]
    return [
        "fallback RAG infra prohibido en beta real: " + fallback
        for fallback in unexpected
    ]


def _technical_summary(response: QueryResponse) -> dict[str, Any]:
    return {
        "status": response.status,
        "sources": response.sources,
        "tool_calls": [
            {
                "tool": call.tool,
                "action": call.action,
                "status": call.status,
                "source": call.source,
                "args": call.args,
                "output_summary": call.output_summary,
                "error": call.error,
            }
            for call in response.tool_calls
        ],
        "fallbacks": response.fallbacks,
        "data": response.data,
        "failure_reason": response.failure_reason,
    }


def _value_at_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")
