import json
import os

from backend.app.cognitive.candidate_bundle_generator import generate_candidate_action_bundles
from backend.app.cognitive.cognitive_operator import run_cognitive_operator
from backend.app.cognitive.llm_client import (
    call_llm,
    extract_first_json_value,
    extract_json_from_llm_text,
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


def sample_prompt() -> str:
    return "Generate candidate bundles for an empty meeting room. Return JSON only."


def assert_json_cleanup() -> None:
    samples = [
        '{"candidate_bundles": []}',
        '`{"candidate_bundles": []}`',
        '```json\n{"candidate_bundles": []}\n```',
        'Here is the plan:\n{"candidate_bundles": []}\nDone.',
        'Text before [{"bundle_name": "array_bundle"}] text after',
    ]

    for sample in samples:
        parsed = extract_json_from_llm_text(sample)
        assert "candidate_bundles" in parsed, f"Failed to parse sample: {sample}"

    first_value = extract_first_json_value("Before ```json\n[{\"bundle_name\": \"array_bundle\"}]\n``` after")
    assert isinstance(first_value, list), "Expected first JSON value helper to preserve arrays."


def assert_provider_trace(result: dict) -> None:
    for key in [
        "selected_provider",
        "attempted_providers",
        "fallback_used",
        "error_summary",
        "model",
        "latency_ms",
        "provider_timeout_seconds",
        "configured_provider_timeout_seconds",
        "retry_count",
        "timed_out",
        "dropped_actions",
        "dropped_bundles",
        "normalized_bundle_count",
        "raw_bundle_count",
    ]:
        assert key in result, f"Missing provider trace key: {key}"


if __name__ == "__main__":
    assert_json_cleanup()

    original = set_env({"FORGEHIVE_LLM_MODE": "mock"})
    mock_result = call_llm(sample_prompt(), {"goal": "reduce_energy_keep_comfort_safe", "event_type": "empty_room_detected"})
    restore_env(original)
    assert_provider_trace(mock_result)

    original = set_env({"FORGEHIVE_LLM_MODE": "disabled"})
    disabled_result = call_llm(sample_prompt())
    disabled_candidate_result = generate_candidate_action_bundles(
        "reduce_energy_keep_comfort_safe",
        "empty_room_detected",
        {"next_meeting_minutes": 90},
    )
    restore_env(original)
    assert_provider_trace(disabled_result)

    original = set_env(
        {
            "FORGEHIVE_LLM_MODE": "auto",
            "FORGEHIVE_LLM_PROVIDER_PRIORITY": "ollama,openrouter,mock",
            "OLLAMA_BASE_URL": "http://127.0.0.1:9",
            "OPENROUTER_API_KEY": None,
        }
    )
    auto_result = call_llm(sample_prompt(), {"goal": "reduce_energy_keep_comfort_safe", "event_type": "empty_room_detected"})
    assert_provider_trace(auto_result)
    candidate_result = generate_candidate_action_bundles(
        "reduce_energy_keep_comfort_safe",
        "empty_room_detected",
        {"next_meeting_minutes": 90},
    )
    cognitive_result = run_cognitive_operator(
        "The meeting room is empty now. Save energy but keep it safe.",
        {"next_meeting_minutes": 90},
    )
    restore_env(original)

    original = set_env(
        {
            "FORGEHIVE_LLM_MODE": "auto",
            "FORGEHIVE_LLM_PROVIDER_PRIORITY": "openrouter,mock",
            "OPENROUTER_API_KEY": None,
        }
    )
    openrouter_missing_result = call_llm(
        sample_prompt(),
        {"goal": "reduce_energy_keep_comfort_safe", "event_type": "empty_room_detected"},
    )
    restore_env(original)

    print(json.dumps({"mock_result": mock_result}, indent=2))
    print(json.dumps({"disabled_result": disabled_result}, indent=2))
    print(json.dumps({"disabled_candidate_generation": {
        "candidate_count": len(disabled_candidate_result.get("candidate_bundles", [])),
        "llm_result": disabled_candidate_result.get("llm_result"),
    }}, indent=2))
    print(json.dumps({"auto_result": auto_result}, indent=2))
    print(json.dumps({"openrouter_missing_result": openrouter_missing_result}, indent=2))
    print(json.dumps({"candidate_generation": {
        "candidate_count": len(candidate_result.get("candidate_bundles", [])),
        "llm_result": candidate_result.get("llm_result"),
    }}, indent=2))
    print(json.dumps({"cognitive_operator": {
        "project": cognitive_result.get("project"),
        "ready_for_layer5": cognitive_result.get("ready_for_layer5"),
        "execution_allowed": cognitive_result.get("execution_allowed"),
        "llm_result": cognitive_result.get("candidate_bundle_generation", {}).get("llm_result"),
    }}, indent=2))

    passed = (
        mock_result["success"] is True
        and mock_result["selected_provider"] == "mock"
        and disabled_result["success"] is False
        and disabled_result["selected_provider"] is None
        and len(disabled_candidate_result.get("candidate_bundles", [])) >= 2
        and disabled_candidate_result.get("llm_result", {}).get("fallback_used") is True
        and auto_result["success"] is True
        and auto_result["selected_provider"] == "mock"
        and "openrouter" in auto_result["attempted_providers"]
        and auto_result["fallback_used"] is True
        and "OPENROUTER_API_KEY is missing" in (auto_result.get("error_summary") or "")
        and openrouter_missing_result["selected_provider"] == "mock"
        and "OPENROUTER_API_KEY is missing" in (openrouter_missing_result.get("error_summary") or "")
        and len(candidate_result.get("candidate_bundles", [])) >= 2
        and all(bundle.get("actions") for bundle in candidate_result.get("candidate_bundles", []))
        and any(
            {"lighting_adjustment", "hvac_setpoint_adjustment", "ventilation_adjustment"}.issubset(
                {action.get("action_type") for action in bundle.get("actions", [])}
            )
            for bundle in candidate_result.get("candidate_bundles", [])
        )
        and cognitive_result["project"]["layer"] == "Layer 4"
        and cognitive_result["execution_allowed"] is False
        and cognitive_result["ready_for_layer5"] is True
    )

    if passed:
        print("\nPhase 4.5 test passed: LLM provider fallback is working.")
    else:
        print("\nPhase 4.5 test failed: LLM provider fallback did not meet expected checks.")
        raise SystemExit(1)
