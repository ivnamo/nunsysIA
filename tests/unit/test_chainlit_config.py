from chainlit_app.config import ChainlitAppSettings


def test_chainlit_backend_timeout_default_allows_real_deepagent_queries() -> None:
    settings = ChainlitAppSettings()

    assert settings.backend_api_timeout_seconds >= 120.0
    assert settings.agent_mode == "deepagent"
