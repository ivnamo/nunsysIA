import asyncio
import logging
import time
from functools import lru_cache
from uuid import uuid4

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
    request_id = str(uuid4())
    started_at = time.perf_counter()
    settings = get_settings()
    mode_label = request.mode.value if request.mode else settings.agent_mode
    try:
        response = await asyncio.wait_for(
            agent_router.query(
                question=request.question,
                conversation_id=request.conversation_id,
                mode=request.mode,
                include_citation_previews=request.include_citation_previews,
            ),
            timeout=settings.agent_execution_timeout_seconds,
        )
        response = _with_request_metadata(response, request_id, started_at)
        log_context = _log_context(request_id, mode_label, response, started_at)
        logger.info(
            "Query completed %s",
            _format_log_context(log_context),
            extra=log_context,
        )
        return response
    except asyncio.TimeoutError as exc:
        log_context = _log_context(request_id, mode_label, None, started_at)
        logger.warning(
            "Query timed out %s",
            _format_log_context(log_context),
            extra=log_context,
        )
        raise _http_error(
            status.HTTP_504_GATEWAY_TIMEOUT,
            request_id,
            started_at,
            "La consulta supero el timeout configurado.",
        ) from exc
    except AgentModeUnavailableError as exc:
        raise _http_error(
            status.HTTP_400_BAD_REQUEST,
            request_id,
            started_at,
            str(exc),
        ) from exc
    except DeepAgentsUnavailableError as exc:
        raise _http_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            request_id,
            started_at,
            str(exc),
        ) from exc
    except DeepAgentsExecutionError as exc:
        raise _http_error(
            status.HTTP_502_BAD_GATEWAY,
            request_id,
            started_at,
            str(exc),
        ) from exc
    except Exception as exc:
        log_context = _log_context(request_id, mode_label, None, started_at)
        logger.exception(
            "Query workflow failed %s",
            _format_log_context(log_context),
            extra=log_context,
        )
        raise _http_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id,
            started_at,
            "No se pudo procesar la consulta de forma controlada.",
        ) from exc


def _with_request_metadata(
    response: QueryResponse,
    request_id: str,
    started_at: float,
) -> QueryResponse:
    metadata = dict(response.metadata or {})
    metadata["request_id"] = request_id
    metadata["duration_ms"] = _duration_ms(started_at)
    return response.model_copy(update={"metadata": metadata})


def _http_error(
    status_code: int,
    request_id: str,
    started_at: float,
    failure_reason: str,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "status": "failed",
            "request_id": request_id,
            "duration_ms": _duration_ms(started_at),
            "failure_reason": failure_reason,
        },
    )


def _log_context(
    request_id: str,
    mode: str,
    response: QueryResponse | None,
    started_at: float,
) -> dict[str, object]:
    return {
        "event": "query_completed" if response is not None else "query_failed",
        "request_id": request_id,
        "agent_mode": mode,
        "duration_ms": _duration_ms(started_at),
        "status": response.status if response is not None else "failed",
        "tool_calls_count": len(response.tool_calls) if response is not None else 0,
        "sources": ",".join(response.sources) if response is not None else "",
        "verification_status": (
            (response.metadata or {}).get("verification_status", "")
            if response is not None
            else ""
        ),
    }


def _duration_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _format_log_context(context: dict[str, object]) -> str:
    return " ".join(
        f"{key}={value}"
        for key, value in context.items()
        if value not in (None, "")
    )
