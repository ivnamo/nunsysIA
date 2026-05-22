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
from app.agents.service import create_query_workflow_service
from app.api.routes_documents import get_document_service
from app.core.config import get_settings
from app.schemas.query import QueryRequest, QueryResponse


router = APIRouter(
    prefix="/api/experimental/deepagents",
    tags=["experimental-deepagents"],
)
logger = logging.getLogger(__name__)


def get_deepagents_query_service() -> DeepAgentsQueryService:
    settings = get_settings()
    if not settings.enable_deepagents_experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "El flujo experimental Deep Agents no esta habilitado. "
                "Configura ENABLE_DEEPAGENTS_EXPERIMENT=true para probarlo."
            ),
        )
    if not deepagents_is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "deepagents no esta instalado. Instala requirements-deepagents.txt "
                "en un entorno compatible para activar este endpoint experimental."
            ),
        )
    return _cached_deepagents_query_service()


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
        logger.exception("Experimental Deep Agents workflow failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo procesar la consulta experimental Deep Agents.",
        ) from exc
