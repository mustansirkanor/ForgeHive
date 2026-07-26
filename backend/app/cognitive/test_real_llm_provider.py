import json
import os

from backend.app.cognitive.llm_client import call_llm


def safe_env_snapshot() -> dict:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    return {
        "FORGEHIVE_LLM_MODE": os.environ.get("FORGEHIVE_LLM_MODE", "mock"),
        "FORGEHIVE_LLM_PROVIDER_PRIORITY": os.environ.get(
            "FORGEHIVE_LLM_PROVIDER_PRIORITY",
            "ollama,openrouter,mock",
        ),
        "OLLAMA_BASE_URL": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        "FORGEHIVE_OLLAMA_MODEL": os.environ.get("FORGEHIVE_OLLAMA_MODEL", "llama3.1:8b"),
        "FORGEHIVE_OLLAMA_TIMEOUT_SECONDS": os.environ.get("FORGEHIVE_OLLAMA_TIMEOUT_SECONDS", "90"),
        "OPENROUTER_MODEL": os.environ.get(
            "OPENROUTER_MODEL",
            "meta-llama/llama-3.1-8b-instruct",
        ),
        "FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS": os.environ.get("FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS", "60"),
        "FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS": os.environ.get("FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS", "140"),
        "OPENROUTER_API_KEY": "present"
        if api_key and api_key != "your_openrouter_key_here"
        else "missing",
    }


def build_smoke_prompt() -> str:
    return (
        "Generate JSON candidate_bundles for an empty room energy saving opportunity. "
        "Use goal reduce_energy_keep_comfort_safe and event_type empty_room_detected. "
        "Return only JSON with a candidate_bundles list. Each bundle should include "
        "candidate actions only, such as lighting_adjustment, hvac_setpoint_adjustment, "
        "and ventilation_adjustment. Do not execute actions."
    )


if __name__ == "__main__":
    context = {
        "goal": "reduce_energy_keep_comfort_safe",
        "event_type": "empty_room_detected",
        "constraints": [
            "Layer 4 generates candidate bundles only.",
            "Do not execute actions.",
            "Layer 5 must simulate, rank, approve, execute, and learn.",
        ],
        "extra_context": {
            "room": "meeting_room",
            "next_meeting_minutes": 90,
        },
    }

    result = call_llm(build_smoke_prompt(), context)
    raw_text = result.get("raw_text") or ""
    dropped_actions = result.get("dropped_actions", [])
    dropped_bundles = result.get("dropped_bundles", [])
    repair_notes = result.get("repair_notes", [])
    candidate_bundles = json.loads(raw_text).get("candidate_bundles", []) if raw_text.strip().startswith("{") else []
    first_candidate_action_types = [
        action.get("action_type")
        for action in (candidate_bundles[0].get("actions", []) if candidate_bundles else [])
    ]

    print(json.dumps({"active_environment_config": safe_env_snapshot()}, indent=2))
    print(
        json.dumps(
            {
                "success": result.get("success"),
                "selected_provider": result.get("selected_provider"),
                "attempted_providers": result.get("attempted_providers"),
                "fallback_used": result.get("fallback_used"),
                "error_summary": result.get("error_summary"),
                "model": result.get("model"),
                "latency_ms": result.get("latency_ms"),
                "provider_timeout_seconds": result.get("provider_timeout_seconds"),
                "configured_provider_timeout_seconds": result.get("configured_provider_timeout_seconds"),
                "retry_count": result.get("retry_count"),
                "timed_out": result.get("timed_out"),
                "schema_repair_applied": result.get("schema_repair_applied"),
                "repair_notes": repair_notes,
                "repair_notes_count": len(repair_notes),
                "dropped_actions_count": len(dropped_actions),
                "dropped_bundles_count": len(dropped_bundles),
                "normalized_bundle_count": result.get("normalized_bundle_count"),
                "raw_bundle_count": result.get("raw_bundle_count"),
                "first_candidate_action_types": first_candidate_action_types,
                "raw_text_first_500_chars": raw_text[:500],
            },
            indent=2,
        )
    )

    if result.get("selected_provider") == "mock":
        print("Real provider was not accepted. Mock is valid only when real providers are unreachable or truly invalid.")
        print(f"Real-provider failure summary: {result.get('error_summary')}")

    print("\nPhase 4.5 real provider smoke test completed.")
