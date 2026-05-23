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
        from deepagents import (
            GeneralPurposeSubagentProfile,
            HarnessProfile,
            create_deep_agent,
            register_harness_profile,
        )
    except ImportError as exc:
        raise DeepAgentsUnavailableError(
            "deepagents esta instalado pero no puede importarse correctamente."
        ) from exc
    register_business_harness_profile(
        kwargs.get("model"),
        general_purpose_subagent=GeneralPurposeSubagentProfile,
        harness_profile=HarnessProfile,
        register_harness_profile=register_harness_profile,
    )
    return create_deep_agent(**kwargs)


def register_business_harness_profile(
    model: Any,
    harness_profile: Any,
    register_harness_profile: Any,
    general_purpose_subagent: Any | None = None,
) -> None:
    if not isinstance(model, str) or not model.strip():
        return
    model_key = model.strip()
    if model_key in REGISTERED_BUSINESS_HARNESS_MODELS:
        return
    profile_kwargs = {"excluded_tools": DEEPAGENTS_BUSINESS_EXCLUDED_TOOLS}
    if general_purpose_subagent is not None:
        profile_kwargs["general_purpose_subagent"] = general_purpose_subagent(
            enabled=False
        )
    register_harness_profile(model_key, harness_profile(**profile_kwargs))
    REGISTERED_BUSINESS_HARNESS_MODELS.add(model_key)
