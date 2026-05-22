import types

import pytest

from app.core.config import Settings
from app.core.llm import LLMProviderError, create_chat_model, create_embedding_model
from app.rag.embeddings import DeterministicEmbeddingModel


def test_create_chat_model_returns_none_for_unconfigured_provider() -> None:
    settings = Settings(llm_provider="deterministic")

    assert create_chat_model(settings) is None


def test_create_embedding_model_returns_deterministic_for_unconfigured_provider() -> None:
    settings = Settings(embedding_provider="deterministic")

    assert isinstance(create_embedding_model(settings), DeterministicEmbeddingModel)


def test_gemini_embeddings_require_api_key() -> None:
    settings = Settings(embedding_provider="gemini", gemini_api_key=None)

    with pytest.raises(LLMProviderError, match="GEMINI_API_KEY"):
        create_embedding_model(settings)


def test_openai_embeddings_require_api_key() -> None:
    settings = Settings(embedding_provider="openai", openai_api_key=None)

    with pytest.raises(LLMProviderError, match="OPENAI_API_KEY"):
        create_embedding_model(settings)


def test_gemini_chat_requires_optional_dependency_when_api_key_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> types.ModuleType:
        if name == "langchain_google_genai":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    settings = Settings(llm_provider="gemini", gemini_api_key="test-key")

    with pytest.raises(LLMProviderError, match="langchain-google-genai"):
        create_chat_model(settings)
