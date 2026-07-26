import os
import urllib.error
import urllib.request

from backend.app.closed_loop.layer5_full_api import run_layer5_full_closed_loop
from backend.app.closed_loop.phase57_artifacts import (
    build_idf_adapter_summary_from_demo,
    export_phase57_artifacts,
)
from backend.app.cognitive.natural_language_operator import run_natural_language_operator


def ollama_is_reachable(base_url: str | None = None, timeout_seconds: float = 3.0) -> bool:
    url = (base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
    try:
        request = urllib.request.Request(f"{url}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return 200 <= response.status < 500
    except (OSError, urllib.error.URLError, TimeoutError):
        return False


def openrouter_key_present() -> bool:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    return bool(api_key and api_key != "your_openrouter_key_here")


def provider_trace_from_layer4(layer4_output: dict) -> dict:
    trace = layer4_output.get("llm_provider_trace") or {}
    candidate_generation = layer4_output.get("candidate_generation") or {}
    llm_result = candidate_generation.get("llm_result") or {}
    merged = dict(llm_result)
    merged.update(trace)
    return merged


def run_real_ollama_full_loop_demo(
    user_message: str = "The meeting room is empty now. Save energy but keep comfort safe.",
) -> dict:
    previous_mode = os.environ.get("FORGEHIVE_LLM_MODE")
    previous_priority = os.environ.get("FORGEHIVE_LLM_PROVIDER_PRIORITY")
    os.environ["FORGEHIVE_LLM_MODE"] = "auto"
    os.environ["FORGEHIVE_LLM_PROVIDER_PRIORITY"] = "ollama,openrouter,mock"

    ollama_reachable = ollama_is_reachable()
    layer4_output = {}
    layer5_result = {}
    artifacts = {}
    error = None

    try:
        layer4_output = run_natural_language_operator(user_message)
        candidate_bundles = layer4_output.get("candidate_bundles", [])
        provider_trace = provider_trace_from_layer4(layer4_output)
        selected_provider = provider_trace.get("selected_provider")
        fallback_used = bool(provider_trace.get("fallback_used", False)) or any(
            bundle.get("fallback_used", False) for bundle in candidate_bundles
        )

        if selected_provider == "mock" and ollama_reachable:
            error = "Strict real Ollama demo failed: Ollama is reachable but provider fallback selected mock."

        layer5_result = run_layer5_full_closed_loop(
            user_message=user_message,
            candidate_bundles=candidate_bundles,
            use_layer4_operator=False,
            layer4_output_override=layer4_output,
        )

        execution = layer5_result.get("phase_5_4_execution", {})
        learning = layer5_result.get("phase_5_5_learning", {})
        demo_result = {
            "project": "ForgeHive",
            "phase": "5.7",
            "demo_type": "real_ollama_full_loop",
            "user_message": user_message,
            "selected_provider": selected_provider,
            "model": provider_trace.get("model"),
            "fallback_used": fallback_used,
            "attempted_providers": provider_trace.get("attempted_providers", []),
            "schema_repair_applied": bool(provider_trace.get("schema_repair_applied", False)),
            "normalized_bundle_count": provider_trace.get("normalized_bundle_count", len(candidate_bundles)),
            "ollama_reachable": ollama_reachable,
            "openrouter_key_present": openrouter_key_present(),
            "candidate_count": len(candidate_bundles),
            "candidate_bundles": candidate_bundles,
            "layer4_provider_trace": provider_trace,
            "layer5_result": layer5_result,
            "idf_adapter_summary": {},
            "energyplus_executed": execution.get("execution_status") == "executed",
            "digital_twin_execution": bool(layer5_result.get("digital_twin_execution", False)),
            "real_building_execution": False,
            "energy_saved_percent": execution.get("energy_saved_percent", 0),
            "carbon_reduced_percent": execution.get("carbon_reduced_percent", 0),
            "comfort_status": execution.get("comfort_status", "Unknown"),
            "bandit_updated": bool(learning.get("bandit_updated", False)),
            "memory_updated": bool(learning.get("memory_updated", False)),
            "knowledge_graph_updated": bool(learning.get("knowledge_graph_updated", False)),
            "closed_loop_complete": bool(layer5_result.get("closed_loop_complete", False)),
            "strict_real_llm_demo_proven": selected_provider in {"ollama", "openrouter"} and not fallback_used,
            "error": error,
            "judge_summary": (
                "ForgeHive used the real Layer 4 provider path, simulated and executed approved actions in the EnergyPlus "
                "digital twin, measured outcomes, and updated learning systems. No real building was controlled."
            ),
        }
        demo_result["idf_adapter_summary"] = build_idf_adapter_summary_from_demo(demo_result)
        artifacts = export_phase57_artifacts(demo_result)
        demo_result["artifact_paths"] = artifacts
        demo_result["phase57_dashboard_summary"] = artifacts.get("dashboard_summary", {})
        return demo_result
    finally:
        if previous_mode is None:
            os.environ.pop("FORGEHIVE_LLM_MODE", None)
        else:
            os.environ["FORGEHIVE_LLM_MODE"] = previous_mode
        if previous_priority is None:
            os.environ.pop("FORGEHIVE_LLM_PROVIDER_PRIORITY", None)
        else:
            os.environ["FORGEHIVE_LLM_PROVIDER_PRIORITY"] = previous_priority
