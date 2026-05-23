from __future__ import annotations

from typing import Any

from app.agents.deepagents_adapter import DeepAgentsUnavailableError, deepagents_is_available


DEEPAGENTS_BUSINESS_EXCLUDED_TOOLS = frozenset(
    {
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
        "task",
    }
)
REGISTERED_BUSINESS_HARNESS_MODELS: set[str] = set()


def create_deep_agent(**kwargs: Any) -> Any:
    if not deepagents_is_available():
        raise DeepAgentsUnavailableError(
            "deepagents no esta instalado. Instala requirements.txt "
            "en un entorno compatible para activar el flujo principal DeepAgents."
        )
    try:
        from deepagents import HarnessProfile, create_deep_agent, register_harness_profile
    except ImportError as exc:
        raise DeepAgentsUnavailableError(
            "deepagents esta instalado pero no puede importarse correctamente."
        ) from exc
    register_business_harness_profile(
        kwargs.get("model"),
        harness_profile=HarnessProfile,
        register_harness_profile=register_harness_profile,
    )
    return create_deep_agent(**kwargs)


def register_business_harness_profile(
    model: Any,
    harness_profile: Any,
    register_harness_profile: Any,
) -> None:
    if not isinstance(model, str) or not model.strip():
        return
    model_key = model.strip()
    if model_key in REGISTERED_BUSINESS_HARNESS_MODELS:
        return
    register_harness_profile(
        model_key,
        harness_profile(excluded_tools=DEEPAGENTS_BUSINESS_EXCLUDED_TOOLS),
    )
    REGISTERED_BUSINESS_HARNESS_MODELS.add(model_key)
