from fastapi import FastAPI

from app.api.routes_documents import router as documents_router
from app.api.routes_health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="nunsysIA",
        version="0.1.0",
        description="POC agentic empresarial con FastAPI, LangGraph, LangChain y RAG.",
    )
    app.include_router(health_router)
    app.include_router(documents_router)
    return app


app = create_app()
