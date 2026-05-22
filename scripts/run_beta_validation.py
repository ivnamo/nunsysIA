from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agents.service import QueryWorkflowService
from app.core.config import Settings, get_settings
from app.core.llm import LLMProviderError, create_chat_model, create_embedding_model
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.production.client import ProductionAPIClient
from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import ChromaDocumentVectorStore, VectorStoreError
from app.schemas.query import QueryRequest, QueryResponse
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.erp_tool import ERPTool
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool
from scripts.beta_validation_support import (
    OBLIGATORY_BETA_CASES,
    BetaCase,
    evaluate_beta_case,
    render_beta_case_report,
)
from scripts.generate_sample_pdfs import SAMPLE_DOCUMENTS, build_pdf_bytes


V2_DOCUMENTS = (
    "v2_anexo_penalizaciones_sla.pdf",
    "v2_contrato_marco_logistica_2026.pdf",
    "v2_procedimiento_produccion_bloqueos.pdf",
    "v2_politica_calidad_entregas.pdf",
    "v2_condiciones_comerciales_northwind.pdf",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta la beta obligatoria opt-in y genera informe Markdown."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Ruta donde escribir el informe. Si se omite, se imprime por stdout.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Anade el informe al final de --output en vez de reemplazarlo.",
    )
    args = parser.parse_args()

    if os.getenv("RUN_REAL_LLM_TESTS") != "1":
        print(
            "RUN_REAL_LLM_TESTS=1 no esta configurado. "
            "Este runner llama al proveedor LLM real configurado en .env.",
            file=sys.stderr,
        )
        return 2

    try:
        service = _build_workflow_service()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    report, exit_code = _run_cases(service, OBLIGATORY_BETA_CASES)
    if args.output:
        mode = "a" if args.append else "w"
        with args.output.open(mode, encoding="utf-8", newline="\n") as file:
            if args.append:
                file.write("\n\n")
            file.write(report)
    else:
        print(report)
    return exit_code


def _run_cases(
    service: QueryWorkflowService,
    cases: tuple[BetaCase, ...],
) -> tuple[str, int]:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sections = [
        "## Validacion beta obligatoria automatizada",
        "",
        f"Fecha de ejecucion: {generated_at}",
        "",
        "Runtime:",
        "",
        "- Flujo en proceso con `QueryWorkflowService`.",
        "- LLM real configurado via `.env`.",
        "- Embeddings reales del proveedor configurado via `.env`.",
        "- ChromaDB persistente local obligatorio para el espacio documental.",
        "- ERP SQLite seed en memoria.",
        "- Production API mockeada en proceso.",
        "- PDFs v2 generados desde `scripts/generate_sample_pdfs.py`.",
        "",
    ]
    totals = {"PASS": 0, "PARTIAL": 0, "FAIL": 0, "BLOCKER": 0}

    for beta_case in cases:
        responses = _execute_case(service, beta_case)
        verdict = evaluate_beta_case(beta_case, responses)
        totals[verdict.status] = totals.get(verdict.status, 0) + 1
        sections.append(render_beta_case_report(beta_case, responses, verdict))

    sections.insert(
        4,
        (
            "- Resultado global: "
            f"PASS={totals['PASS']}, PARTIAL={totals['PARTIAL']}, "
            f"FAIL={totals['FAIL']}, BLOCKER={totals['BLOCKER']}."
        ),
    )
    exit_code = 0 if totals["FAIL"] == 0 and totals["BLOCKER"] == 0 else 1
    return "\n".join(sections), exit_code


def _execute_case(
    service: QueryWorkflowService,
    beta_case: BetaCase,
) -> list[QueryResponse]:
    responses: list[QueryResponse] = []
    conversation_id = f"beta-obligatory-{beta_case.case_id.lower()}"
    for turn in beta_case.turns:
        responses.append(
            service.run(
                QueryRequest(
                    question=turn.question,
                    conversation_id=conversation_id,
                )
            )
        )
    return responses


def _build_workflow_service() -> QueryWorkflowService:
    chat_model = _create_real_chat_model()
    connection = create_sqlite_connection()
    load_seed_sql(connection)
    repository = NorthwindRepository(connection)

    production_client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=_production_transport(),
    )
    document_service = _create_real_document_service(V2_DOCUMENTS)
    vector_store = document_service.vector_store
    embedding_model = document_service.embedding_model

    return QueryWorkflowService(
        erp_tool=ERPTool(repository),
        production_tool=ProductionAPITool(production_client),
        erp_query_tool=ERPQueryTool(repository),
        production_query_tool=ProductionQueryTool(production_client),
        rag_tool=DocumentRAGTool(
            vector_store=vector_store,
            embedding_model=embedding_model,
        ),
        chat_model=chat_model,
        llm_timeout_seconds=_real_llm_timeout_seconds(),
    )


def _create_real_document_service(
    filenames: tuple[str, ...],
) -> DocumentIngestionService:
    settings = _real_rag_settings()
    embedding_model = create_embedding_model(settings)
    collection_name = _unique_beta_collection_name(settings.chroma_collection)
    persist_directory = _beta_chroma_directory(collection_name)
    try:
        vector_store = ChromaDocumentVectorStore(
            mode="persistent",
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection_name=collection_name,
            persist_directory=str(persist_directory),
        )
    except VectorStoreError as exc:
        raise RuntimeError(
            "La beta real requiere ChromaDB persistente; no se permite "
            "FALLBACK_VECTOR_STORE_IN_MEMORY."
        ) from exc

    document_service = DocumentIngestionService(
        vector_store=vector_store,
        embedding_model=embedding_model,
    )
    for filename in filenames:
        document_service.ingest_pdf(
            content=build_pdf_bytes(SAMPLE_DOCUMENTS[filename]),
            filename=filename,
        )
    _assert_no_rag_infra_fallbacks(document_service.fallbacks)
    return document_service


def _real_rag_settings() -> Settings:
    base_settings = get_settings()
    provider = (
        os.getenv("REAL_EMBEDDING_PROVIDER")
        or (
            base_settings.embedding_provider
            if base_settings.embedding_provider in {"gemini", "openai"}
            else None
        )
        or (
            base_settings.llm_provider
            if base_settings.llm_provider in {"gemini", "openai"}
            else None
        )
        or ("gemini" if base_settings.gemini_api_key else None)
        or ("openai" if base_settings.openai_api_key else None)
    )
    if provider is None:
        raise RuntimeError(
            "Configura REAL_EMBEDDING_PROVIDER=gemini/openai o un proveedor de "
            "embeddings real en `.env`; no se permite "
            "FALLBACK_EMBEDDINGS_DETERMINISTIC."
        )
    if provider == "gemini" and not base_settings.gemini_api_key:
        raise RuntimeError("REAL_EMBEDDING_PROVIDER=gemini requiere GEMINI_API_KEY.")
    if provider == "openai" and not base_settings.openai_api_key:
        raise RuntimeError("REAL_EMBEDDING_PROVIDER=openai requiere OPENAI_API_KEY.")

    return base_settings.model_copy(
        update={
            "embedding_provider": provider,
            "chroma_mode": "persistent",
        }
    )


def _unique_beta_collection_name(base_name: str) -> str:
    safe_base = "".join(
        character.lower() if character.isalnum() else "_"
        for character in base_name.strip()
    ).strip("_")
    return f"{safe_base or 'documents'}_beta_{uuid4().hex[:12]}"


def _beta_chroma_directory(collection_name: str) -> Path:
    path = ROOT / ".pytest-tmp" / "beta_chroma" / collection_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _assert_no_rag_infra_fallbacks(fallbacks: list[str]) -> None:
    forbidden = (
        "FALLBACK_VECTOR_STORE_IN_MEMORY",
        "FALLBACK_EMBEDDINGS_DETERMINISTIC",
    )
    unexpected = [
        fallback
        for fallback in fallbacks
        if fallback.startswith(forbidden)
    ]
    if unexpected:
        raise RuntimeError(
            "La beta real no permite fallbacks de infraestructura RAG: "
            + "; ".join(unexpected)
        )


def _create_real_chat_model() -> object:
    settings = _real_llm_settings()
    try:
        chat_model = create_chat_model(settings)
    except LLMProviderError as exc:
        raise RuntimeError(str(exc)) from exc
    if chat_model is None:
        raise RuntimeError("No hay proveedor LLM real configurado.")
    return chat_model


def _real_llm_settings() -> Settings:
    base_settings = get_settings()
    provider = (
        os.getenv("REAL_LLM_PROVIDER")
        or (
            base_settings.llm_provider
            if base_settings.llm_provider in {"gemini", "openai"}
            else None
        )
        or ("gemini" if base_settings.gemini_api_key else None)
        or ("openai" if base_settings.openai_api_key else None)
    )
    if provider is None:
        raise RuntimeError(
            "Configura GEMINI_API_KEY/GEMINI_API_KEY_FILE u "
            "OPENAI_API_KEY/OPENAI_API_KEY_FILE para la beta real."
        )
    if provider == "gemini" and not base_settings.gemini_api_key:
        raise RuntimeError("REAL_LLM_PROVIDER=gemini requiere GEMINI_API_KEY.")
    if provider == "openai" and not base_settings.openai_api_key:
        raise RuntimeError("REAL_LLM_PROVIDER=openai requiere OPENAI_API_KEY.")

    return base_settings.model_copy(
        update={
            "llm_provider": provider,
            "llm_temperature": 0.0,
            "llm_timeout_seconds": _real_llm_timeout_seconds(),
        }
    )


def _real_llm_timeout_seconds() -> float:
    return float(os.getenv("REAL_LLM_TIMEOUT_SECONDS", "90"))


def _production_transport() -> httpx.MockTransport:
    orders = {
        10248: {
            "order_id": 10248,
            "production_status": "in_progress",
            "blocked_reason": None,
            "delay_reason": None,
            "estimated_finish_date": "2026-05-22",
        },
        10252: {
            "order_id": 10252,
            "production_status": "blocked",
            "blocked_reason": "Falta de material",
            "delay_reason": None,
            "estimated_finish_date": "2026-05-30",
        },
        10255: {
            "order_id": 10255,
            "production_status": "finished",
            "blocked_reason": None,
            "delay_reason": None,
            "estimated_finish_date": "2026-05-14",
        },
        10301: {
            "order_id": 10301,
            "production_status": "delayed",
            "blocked_reason": None,
            "delay_reason": "Averia en linea de produccion",
            "estimated_finish_date": "2026-06-03",
        },
        10312: {
            "order_id": 10312,
            "production_status": "blocked",
            "blocked_reason": "Falta de capacidad",
            "delay_reason": None,
            "estimated_finish_date": "2026-06-02",
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/production/orders":
            status = request.url.params.get("status")
            filtered_orders = list(orders.values())
            if status:
                filtered_orders = [
                    order
                    for order in filtered_orders
                    if order["production_status"] == status
                ]
            return httpx.Response(200, json={"orders": filtered_orders})

        if request.url.path.startswith("/production/orders/"):
            order_id = int(request.url.path.rsplit("/", 1)[1])
            order = orders.get(order_id)
            if order is None:
                return httpx.Response(
                    404,
                    json={"detail": "Production order not found"},
                )
            return httpx.Response(200, json=order)

        return httpx.Response(500, text="unexpected path")

    return httpx.MockTransport(handler)


if __name__ == "__main__":
    raise SystemExit(main())
