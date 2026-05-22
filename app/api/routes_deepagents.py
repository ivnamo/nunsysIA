import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.deepagents_adapter import deepagents_is_available
from app.agents.deepagents_service import (
    DeepAgentsExecutionError,
    DeepAgentsQueryService,
    DeepAgentsUnavailableError,
    create_deepagents_query_service,
)
from app.agents.deepagents_tools_service import (
    DeepAgentsToolsQueryService,
    create_deepagents_tools_query_service,
)
from app.agents.service import (
    _create_erp_tools,
    _create_production_tools,
    create_query_workflow_service,
)
from app.api.routes_documents import get_document_service
from app.core.config import get_settings
from app.schemas.query import QueryRequest, QueryResponse
from app.tools.rag_tool import DocumentRAGTool


router = APIRouter(
    prefix="/api/experimental/deepagents",
    tags=["experimental-legacy-deepagents"],
)
logger = logging.getLogger(__name__)


def get_deepagents_query_service() -> DeepAgentsQueryService:
    _ensure_deepagents_experiment_enabled()
    return _cached_deepagents_query_service()


def get_deepagents_tools_query_service() -> DeepAgentsToolsQueryService:
    _ensure_deepagents_experiment_enabled()
    return _cached_deepagents_tools_query_service()


@lru_cache
def _cached_deepagents_query_service() -> DeepAgentsQueryService:
    settings = get_settings()
    workflow = create_query_workflow_service(
        settings=settings,
        document_service=get_document_service(),
    )
    return create_deepagents_query_service(
        settings=settings,
        workflow=workflow,
    )


@lru_cache
def _cached_deepagents_tools_query_service() -> DeepAgentsToolsQueryService:
    settings = get_settings()
    erp_tool, erp_query_tool = _create_erp_tools()
    production_tool, production_query_tool = _create_production_tools(settings)
    document_service = get_document_service()
    return create_deepagents_tools_query_service(
        settings=settings,
        erp_tool=erp_tool,
        production_tool=production_tool,
        erp_query_tool=erp_query_tool,
        production_query_tool=production_query_tool,
        rag_tool=DocumentRAGTool(
            vector_store=document_service.vector_store,
            embedding_model=document_service.embedding_model,
        ),
    )


@router.post("/query", response_model=QueryResponse)
def query_deepagents(
    request: QueryRequest,
    service: DeepAgentsQueryService = Depends(get_deepagents_query_service),
) -> QueryResponse:
    try:
        return service.run(request)
    except DeepAgentsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except DeepAgentsExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Experimental DeepAgents sidecar workflow failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo procesar la consulta experimental DeepAgents sidecar.",
        ) from exc


@router.post("/tools/query", response_model=QueryResponse)
def query_deepagents_tools(
    request: QueryRequest,
    service: DeepAgentsToolsQueryService = Depends(get_deepagents_tools_query_service),
) -> QueryResponse:
    try:
        return service.run(request)
    except DeepAgentsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Experimental legacy DeepAgents direct-tools workflow failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo procesar la consulta experimental legacy DeepAgents tools.",
        ) from exc


def _ensure_deepagents_experiment_enabled() -> None:
    settings = get_settings()
    if not settings.enable_deepagents_experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "El endpoint experimental heredado de DeepAgents no esta "
                "habilitado. El flujo principal esta en POST /api/query con "
                "mode=deepagent. Configura ENABLE_DEEPAGENTS_EXPERIMENT=true "
                "solo para comparativa tecnica."
            ),
        )
    if not deepagents_is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "deepagents no esta instalado. Instala requirements.txt "
                "en un entorno compatible para activar este endpoint experimental."
            ),
        )
