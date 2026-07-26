import json
import os

from backend.app.cognitive.llm_client import call_llm


def api_key_present() -> bool:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    return bool(api_key and api_key != "your_openrouter_key_here")


def looks_like_unreachable_ollama(error_summary: str) -> bool:
    text = (error_summary or "").lower()
    return any(
        phrase in text
        for phrase in [
            "connection refused",
            "actively refused",
            "timed out",
            "no connection could be made",
            "failed to establish",
            "name or service not known",
        ]
    )


if __name__ == "__main__":
    context = {
        "goal": "reduce_energy_keep_comfort_safe",
        "event_type": "empty_room_detected",
        "constraints": [
            "Layer 4 generates candidate bundles only.",
            "Layer 5 simulates, ranks, approves, executes, and learns.",
        ],
        "extra_context": {"contract_test": True},
    }
    prompt = (
        "Return only JSON with candidate_bundles for an empty room energy-saving opportunity. "
        "Use only ForgeHive canonical action types and do not execute actions."
    )

    result = call_llm(prompt, context)
    raw_text = result.get("raw_text") or "{}"
    parsed = json.loads(raw_text) if raw_text.strip().startswith("{") else {}
    candidate_count = len(parsed.get("candidate_bundles", []))
    selected_provider = result.get("selected_provider")
    error_summary = result.get("error_summary") or ""

    print(
        json.dumps(
            {
                "selected_provider": selected_provider,
                "attempted_providers": result.get("attempted_providers"),
                "fallback_used": result.get("fallback_used"),
                "error_summary": error_summary,
                "schema_repair_applied": result.get("schema_repair_applied"),
                "repair_notes": result.get("repair_notes"),
                "dropped_actions": result.get("dropped_actions"),
                "dropped_bundles": result.get("dropped_bundles"),
                "normalized_bundle_count": result.get("normalized_bundle_count"),
                "raw_bundle_count": result.get("raw_bundle_count"),
                "candidate_count": candidate_count,
            },
            indent=2,
        )
    )

    if selected_provider in {"ollama", "openrouter"}:
        assert candidate_count > 0
        print("Phase 4.6.1 real provider contract passed with real provider.")
    elif selected_provider == "mock":
        if api_key_present():
            raise SystemExit(
                "Real provider contract failed: OpenRouter API key is present but only mock was selected. "
                f"Schema/provider issue: {error_summary}"
            )
        if "ollama:" in error_summary.lower() and not looks_like_unreachable_ollama(error_summary):
            raise SystemExit(
                "Real provider contract failed: Ollama appeared reachable but only mock was selected. "
                f"Schema/provider issue: {error_summary}"
            )
        print("Phase 4.6.1 real provider contract completed with mock because no real provider was available.")
    else:
        raise SystemExit(f"Unexpected selected provider: {selected_provider}")
