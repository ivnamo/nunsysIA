from urllib.parse import urljoin

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse, ReadinessCheck, ReadinessResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse()


@router.get("/health/ready", response_model=ReadinessResponse)
def readiness_check() -> JSONResponse:
    settings = get_settings()
    checks = {
        "production_api": _check_http(
            urljoin(settings.production_api_base_url.rstrip("/") + "/", "health"),
            accepted_statuses={200},
        ),
        "chroma": _check_chroma(settings),
        "llm_provider": _check_llm_provider(settings),
        "embedding_provider": _check_embedding_provider(settings),
    }
    ready = all(check.status == "ok" for check in checks.values())
    payload = ReadinessResponse(
        status="ok" if ready else "degraded",
        checks=checks,
    )
    return JSONResponse(
        status_code=200 if ready else 503,
        content=payload.model_dump(),
    )


def _check_chroma(settings: Settings) -> ReadinessCheck:
    if settings.chroma_mode == "persistent":
        return ReadinessCheck(
            status="ok",
            detail=f"persistent:{settings.chroma_persist_directory}",
        )
    if settings.chroma_mode != "http":
        return ReadinessCheck(
            status="error",
            detail=f"modo Chroma no soportado: {settings.chroma_mode}",
        )
    url = f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat"
    return _check_http(url, accepted_statuses={200, 404})


def _check_llm_provider(settings: Settings) -> ReadinessCheck:
    provider = settings.llm_provider.strip().lower()
    if provider == "deterministic":
        return ReadinessCheck(status="ok", detail="deterministic")
    if provider == "gemini" and settings.gemini_api_key:
        return ReadinessCheck(status="ok", detail="gemini")
    if provider == "openai" and settings.openai_api_key:
        return ReadinessCheck(status="ok", detail="openai")
    if provider not in {"gemini", "openai"}:
        return ReadinessCheck(status="error", detail=f"proveedor LLM no soportado: {provider}")
    return ReadinessCheck(status="error", detail=f"{provider} sin API key configurada")


def _check_embedding_provider(settings: Settings) -> ReadinessCheck:
    provider = settings.embedding_provider.strip().lower()
    if provider == "gemini" and settings.gemini_api_key:
        return ReadinessCheck(status="ok", detail="gemini")
    if provider == "openai" and settings.openai_api_key:
        return ReadinessCheck(status="ok", detail="openai")
    if provider not in {"gemini", "openai"}:
        return ReadinessCheck(
            status="error",
            detail=f"proveedor de embeddings no soportado: {provider}",
        )
    return ReadinessCheck(status="error", detail=f"{provider} sin API key configurada")


def _check_http(url: str, *, accepted_statuses: set[int]) -> ReadinessCheck:
    try:
        response = httpx.get(url, timeout=2.0)
    except httpx.HTTPError as exc:
        return ReadinessCheck(status="error", detail=str(exc))
    if response.status_code in accepted_statuses:
        return ReadinessCheck(status="ok", detail=f"HTTP {response.status_code}")
    return ReadinessCheck(
        status="error",
        detail=f"HTTP {response.status_code}: {response.text[:120]}",
    )
