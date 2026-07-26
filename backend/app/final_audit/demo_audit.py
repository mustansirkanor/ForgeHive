import json
from pathlib import Path

from backend.app.closed_loop.real_llm_full_loop import (
    ollama_is_reachable,
    openrouter_key_present,
    run_real_ollama_full_loop_demo,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "final_submission"
OUTPUT_FILE = OUTPUT_DIR / "forgehive_final_demo_audit.json"
DEMO_MESSAGE = "The meeting room is empty now. Save energy but keep comfort safe."


def add_check(checks: list[dict], name: str, passed: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


def run_final_demo_audit() -> dict:
    checks = []
    errors = []
    demo_result = {}
    real_provider_available = ollama_is_reachable() or openrouter_key_present()

    try:
        demo_result = run_real_ollama_full_loop_demo(DEMO_MESSAGE)
    except Exception as exc:
        errors.append(str(exc))

    dashboard = demo_result.get("phase57_dashboard_summary", {})
    layer5 = demo_result.get("layer5_result", {})
    final_dashboard = layer5.get("phase_5_6_dashboard", {})
    adapter = demo_result.get("idf_adapter_summary", {})

    selected_provider = demo_result.get("selected_provider")
    add_check(checks, "real_provider_selected", selected_provider in {"ollama", "openrouter"}, f"selected_provider={selected_provider}")
    add_check(checks, "mock_not_used_when_real_available", not (real_provider_available and selected_provider == "mock"), f"real_provider_available={real_provider_available}")
    add_check(checks, "candidate_count_positive", demo_result.get("candidate_count", 0) > 0)
    add_check(checks, "dashboard_candidate_count_positive", dashboard.get("candidateBundlesGenerated", 0) > 0)
    add_check(checks, "energyplus_executed", demo_result.get("energyplus_executed") is True)
    add_check(checks, "digital_twin_execution", demo_result.get("digital_twin_execution") is True)
    add_check(checks, "real_building_execution_false", demo_result.get("real_building_execution") is False and dashboard.get("realBuildingExecution") is False)
    add_check(checks, "safety_governor_used", final_dashboard.get("safetyGovernorUsed") is True or dashboard.get("safetyGovernorUsed") is True)
    add_check(checks, "rl_bandit_used", final_dashboard.get("rlBanditUsed") is True or dashboard.get("rlBanditUsed") is True)
    add_check(checks, "knowledge_graph_used", final_dashboard.get("knowledgeGraphUsed") is True or dashboard.get("knowledgeGraphUsed") is True)
    add_check(checks, "learning_updated", any(bool(demo_result.get(key)) for key in ["memory_updated", "bandit_updated", "knowledge_graph_updated"]))
    add_check(checks, "lighting_idf_applied", adapter.get("lighting_applied") is True)
    add_check(
        checks,
        "hvac_idf_applied_or_honest",
        adapter.get("hvac_setpoint_applied") is True
        or any(action.get("action_type") == "hvac_setpoint_adjustment" for action in adapter.get("metadata_only_actions", [])),
    )
    add_check(
        checks,
        "ventilation_idf_applied_or_honest",
        adapter.get("ventilation_applied") is True
        or any(action.get("action_type") == "ventilation_adjustment" for action in adapter.get("metadata_only_actions", [])),
    )
    add_check(checks, "comfort_not_unsafe", demo_result.get("comfort_status") in {"Safe", "Warning"})
    add_check(checks, "closed_loop_complete", demo_result.get("closed_loop_complete") is True)
    add_check(checks, "judge_ready", dashboard.get("judgeReady") is True)
    add_check(checks, "dashboard_adapter_consistent", dashboard.get("lightingAppliedInIDF") == adapter.get("lighting_applied"))
    add_check(checks, "dashboard_hvac_consistent", dashboard.get("hvacSetpointAppliedInIDF") == adapter.get("hvac_setpoint_applied"))
    add_check(checks, "dashboard_ventilation_consistent", dashboard.get("ventilationAppliedInIDF") == adapter.get("ventilation_applied"))

    failed_checks = [check for check in checks if not check["passed"]]
    audit = {
        "user_message": DEMO_MESSAGE,
        "real_provider_available": real_provider_available,
        "selected_provider": selected_provider,
        "checks": checks,
        "failed_checks": failed_checks,
        "errors": errors,
        "demo_result": demo_result,
        "audit_passed": not failed_checks and not errors,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(audit, indent=2))
    return audit


if __name__ == "__main__":
    print(json.dumps(run_final_demo_audit(), indent=2))
