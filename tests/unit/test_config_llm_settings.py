from app.core.config import Settings, get_settings


def test_settings_default_gemini_model_is_current_flash_model() -> None:
    settings = Settings()

    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.gemini_api_transport == "rest"


def test_settings_load_llm_and_embedding_provider_env(
    monkeypatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("GEMINI_API_TRANSPORT", "grpc")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "8")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    settings = get_settings()

    assert settings.llm_provider == "openai"
    assert settings.openai_api_key == "test-openai-key"
    assert settings.openai_model == "gpt-4o-mini"
    assert settings.gemini_api_transport == "grpc"
    assert settings.embedding_provider == "openai"
    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.llm_timeout_seconds == 8.0

    get_settings.cache_clear()


def test_settings_convert_empty_api_keys_to_none(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", " ")

    settings = get_settings()

    assert settings.gemini_api_key is None
    assert settings.openai_api_key is None

    get_settings.cache_clear()


def test_settings_prefers_erp_database_url_over_chainlit_database_url(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql://chainlit:chainlit@localhost:5432/chainlit")
    monkeypatch.setenv(
        "ERP_DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@postgres:5432/northwind",
    )

    settings = get_settings()

    assert settings.database_url.startswith("postgresql+psycopg://")

    get_settings.cache_clear()
