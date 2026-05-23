from typing import Any, Protocol

from app.core.config import Settings
from app.rag.embeddings import DeterministicEmbeddingModel, EmbeddingModel


class LLMProviderError(RuntimeError):
    pass


class ChatModel(Protocol):
    def invoke(self, input: Any, **kwargs: Any) -> Any:
        ...


def create_chat_model(settings: Settings) -> ChatModel | None:
    provider = settings.llm_provider.lower()
    if provider == "gemini":
        return _create_gemini_chat_model(settings)
    if provider == "openai":
        return _create_openai_chat_model(settings)
    return None


def create_embedding_model(settings: Settings) -> EmbeddingModel:
    provider = settings.embedding_provider.lower()
    if provider == "gemini":
        return _create_gemini_embeddings(settings)
    if provider == "openai":
        return _create_openai_embeddings(settings)
    if provider == "deterministic":
        return DeterministicEmbeddingModel()
    raise LLMProviderError(
        "EMBEDDING_PROVIDER debe ser gemini, openai o deterministic."
    )


def _create_gemini_chat_model(settings: Settings) -> ChatModel | None:
    if not settings.gemini_api_key:
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError as exc:
        raise LLMProviderError(
            "LLM_PROVIDER=gemini requiere instalar langchain-google-genai."
        ) from exc

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=settings.llm_temperature,
        request_timeout=settings.llm_timeout_seconds,
        retries=0,
    )


def _create_openai_chat_model(settings: Settings) -> ChatModel | None:
    if not settings.openai_api_key:
        return None

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise LLMProviderError(
            "LLM_PROVIDER=openai requiere instalar langchain-openai."
        ) from exc

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=0,
    )


def _create_gemini_embeddings(settings: Settings) -> EmbeddingModel:
    if not settings.gemini_api_key:
        raise LLMProviderError(
            "EMBEDDING_PROVIDER=gemini requiere GEMINI_API_KEY o GEMINI_API_KEY_FILE."
        )

    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
    except ImportError as exc:
        raise LLMProviderError(
            "EMBEDDING_PROVIDER=gemini requiere instalar langchain-google-genai."
        ) from exc

    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
        transport=settings.gemini_api_transport,
    )


def _create_openai_embeddings(settings: Settings) -> EmbeddingModel:
    if not settings.openai_api_key:
        raise LLMProviderError(
            "EMBEDDING_PROVIDER=openai requiere OPENAI_API_KEY o OPENAI_API_KEY_FILE."
        )

    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError as exc:
        raise LLMProviderError(
            "EMBEDDING_PROVIDER=openai requiere instalar langchain-openai."
        ) from exc

    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
