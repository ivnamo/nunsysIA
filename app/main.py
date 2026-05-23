from fastapi import FastAPI

from app.api.routes_deepagents import router as deepagents_router
from app.api.routes_documents import router as documents_router
from app.api.routes_health import router as health_router
from app.api.routes_query import router as query_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(get_settings().log_level)
    app = FastAPI(
        title="nunsysIA",
        version="0.1.0",
        description=(
            "Sistema agentic empresarial con FastAPI, LangChain DeepAgents, "
            "LangChain tools y RAG."
        ),
    )
    app.include_router(health_router)
    app.include_router(query_router)
    app.include_router(deepagents_router)
    app.include_router(documents_router)
    return app


app = create_app()
