import os

from backend.app.cognitive import llm_client
from backend.app.cognitive.mcp_tool_registry import (
    execute_mcp_tool,
    get_layer4_guardrail_summary,
)


def set_env(updates: dict) -> dict:
    original = {}
    for key, value in updates.items():
        original[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return original


def restore_env(original: dict) -> None:
    for key, value in original.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def sample_context() -> dict:
    return {
        "goal": "reduce_energy_keep_comfort_safe",
        "event_type": "empty_room_detected",
        "extra_context": {"next_meeting_minutes": 90},
    }


if __name__ == "__main__":
    original = set_env(
        {
            "FORGEHIVE_OLLAMA_TIMEOUT_SECONDS": None,
            "FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS": None,
            "FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS": None,
        }
    )
    assert llm_client.get_ollama_timeout_seconds() == 90.0
    assert llm_client.get_openrouter_timeout_seconds() == 60.0
    assert llm_client.get_llm_total_timeout_seconds() == 140.0
    restore_env(original)

    original = set_env(
        {
            "FORGEHIVE_OLLAMA_TIMEOUT_SECONDS": "12.5",
            "FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS": "8",
            "FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS": "33",
        }
    )
    assert llm_client.get_ollama_timeout_seconds() == 12.5
    assert llm_client.get_openrouter_timeout_seconds() == 8.0
    assert llm_client.get_llm_total_timeout_seconds() == 33.0
    restore_env(original)

    original_ollama_call = llm_client.call_ollama_llm
    observed_timeouts = []

    def timed_out_ollama(prompt: str, model: str | None = None, timeout_seconds: float | None = None) -> str:
        observed_timeouts.append(timeout_seconds)
        raise TimeoutError("timed out")

    llm_client.call_ollama_llm = timed_out_ollama
    original = set_env(
        {
            "FORGEHIVE_LLM_MODE": "auto",
            "FORGEHIVE_LLM_PROVIDER_PRIORITY": "ollama,mock",
            "FORGEHIVE_OLLAMA_TIMEOUT_SECONDS": "3",
            "FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS": "4",
            "FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS": "20",
        }
    )
    try:
        result = llm_client.call_llm(
            "Generate candidate_bundles JSON for an empty room. Do not execute actions.",
            sample_context(),
        )
    finally:
        restore_env(original)
        llm_client.call_ollama_llm = original_ollama_call

    assert result["success"] is True
    assert result["selected_provider"] == "mock"
    assert result["attempted_providers"] == ["ollama", "mock"]
    assert result["fallback_used"] is True
    assert result["retry_count"] == 1
    assert result["timed_out"] is True
    assert result["provider_timeout_seconds"] == 0.0
    assert result["configured_provider_timeout_seconds"]["ollama"] == 3.0
    assert result["configured_provider_timeout_seconds"]["openrouter"] == 4.0
    assert result["configured_provider_timeout_seconds"]["total"] == 20.0
    assert observed_timeouts == [3.0, 3.0]
    assert "timed out" in (result.get("error_summary") or "")

    guardrails = get_layer4_guardrail_summary()
    blocked_execution_result = execute_mcp_tool("apply_approved_action_bundle", {"demo": True})
    assert guardrails["llm_can_execute_actions"] is False
    assert guardrails["energyplus_execution_enabled"] is False
    assert blocked_execution_result["success"] is False
    assert blocked_execution_result["allowed"] is False

    print("Phase 4.5.2 timeout config test passed.")
