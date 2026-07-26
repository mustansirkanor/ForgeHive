import json
from pathlib import Path

from backend.app.decision.decision_api import (
    get_autonomous_decision,
    get_dashboard_ready_decision,
    save_decision_artifacts,
)


if __name__ == "__main__":
    energy_decision = get_autonomous_decision("reduce energy while keeping comfort safe")
    carbon_decision = get_autonomous_decision("reduce carbon impact today")
    anomaly_decision = get_autonomous_decision("fix building issues and anomalies")
    dashboard_decision = get_dashboard_ready_decision("reduce energy")
    saved = save_decision_artifacts("reduce carbon impact today")

    print(json.dumps(energy_decision, indent=2))
    print(json.dumps(carbon_decision, indent=2))
    print(json.dumps(anomaly_decision, indent=2))
    print(json.dumps(dashboard_decision, indent=2))
    print(json.dumps(saved, indent=2))

    carbon_plan = carbon_decision["supporting_outputs"].get("carbon_plan")
    carbon_selected_action = carbon_decision["decision"].get("selected_action") or {}
    generated_files = saved["generated_files"]
    saved_files_exist = all(Path(path).exists() for path in generated_files.values())

    passed = (
        bool(energy_decision.get("project"))
        and bool(energy_decision.get("decision"))
        and (
            not energy_decision["decision"]["ready_for_execution"]
            or energy_decision["decision"]["selected_action"] is not None
        )
        and bool(energy_decision["decision"].get("safety_decision"))
        and isinstance(energy_decision["decision"].get("ready_for_execution"), bool)
        and carbon_plan is not None
        and carbon_decision["decision"]["selected_plan_type"] in ["carbon_aware_schedule", "supervisor"]
        and (
            carbon_decision["decision"]["selected_plan_type"] != "carbon_aware_schedule"
            or carbon_selected_action.get("action_type") == "carbon_schedule_shift"
        )
        and bool(anomaly_decision["supporting_outputs"].get("supervisor_decision"))
        and bool(anomaly_decision["decision"].get("safety_decision"))
        and "selectedStrategy" in dashboard_decision
        and "approved" in dashboard_decision
        and "riskLevel" in dashboard_decision
        and saved_files_exist
    )

    if passed:
        print("\nPhase 3.5 and 3.6 test passed: Carbon-aware scheduling and decision API are working.")
    else:
        print("\nPhase 3.5 and 3.6 test failed: Decision API did not meet expected checks.")
        raise SystemExit(1)
