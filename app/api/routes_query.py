import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.service import QueryWorkflowService, create_query_workflow_service
from app.api.routes_documents import get_document_service
from app.core.config import get_settings
from app.schemas.query import QueryRequest, QueryResponse


router = APIRouter(prefix="/api", tags=["query"])
logger = logging.getLogger(__name__)


@lru_cache
def get_query_service() -> QueryWorkflowService:
    return create_query_workflow_service(
        settings=get_settings(),
        document_service=get_document_service(),
    )


@router.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    service: QueryWorkflowService = Depends(get_query_service),
) -> QueryResponse:
    try:
        return service.run(request)
    except Exception as exc:
        logger.exception("Query workflow failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo procesar la consulta de forma controlada.",
        ) from exc
