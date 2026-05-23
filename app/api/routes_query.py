import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.deepagents_adapter import DeepAgentsUnavailableError
from app.agents.deepagents_service import DeepAgentsExecutionError
from app.agents.router import AgentModeUnavailableError, AgentRouter
from app.api.routes_documents import get_document_service
from app.core.config import get_settings
from app.schemas.query import QueryRequest, QueryResponse
from app.services.agent_service import create_agent_router


router = APIRouter(prefix="/api", tags=["query"])
logger = logging.getLogger(__name__)


@lru_cache
def get_agent_router() -> AgentRouter:
    return create_agent_router(
        settings=get_settings(),
        document_service=get_document_service(),
    )


get_query_service = get_agent_router


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    agent_router: AgentRouter = Depends(get_agent_router),
) -> QueryResponse:
    try:
        return await agent_router.query(
            question=request.question,
            conversation_id=request.conversation_id,
            mode=request.mode,
            include_citation_previews=request.include_citation_previews,
        )
    except AgentModeUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
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
        logger.exception("Query workflow failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo procesar la consulta de forma controlada.",
        ) from exc
