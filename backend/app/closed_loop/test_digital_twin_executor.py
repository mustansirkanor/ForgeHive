import json
from pathlib import Path

from backend.app.closed_loop.digital_twin_executor import (
    build_execution_bundle_from_safety_approval,
    execute_approved_bundle_in_digital_twin,
)
from backend.app.energyplus import config as energyplus_config


APPROVED_ACTION = {
    "action_id": "approved_lighting",
    "strategy_name": "eco_mode",
    "action_type": "lighting_adjustment",
    "target": "unoccupied_zones",
    "description": "Dim lights in empty room.",
    "parameters": {"lighting_level_percent": 25, "applies_to_occupied_zones": False},
    "expected_energy_saved_percent": 5.0,
    "expected_carbon_reduced_percent": 5.0,
    "expected_comfort_impact": "neutral",
    "source_agent": "test",
    "priority": "medium",
}

REJECTED_ACTION = {
    "action": {
        "action_id": "rejected_hvac",
        "action_type": "hvac_setpoint_adjustment",
        "parameters": {"cooling_setpoint_c": 35},
    },
    "decision": {"approved": False, "risk_level": "high"},
}


def plan(execution_ready: bool = True) -> dict:
    return {
        "project": {"name": "ForgeHive", "layer": "Layer 5", "phase": "5.1-5.3"},
        "baseline": {"energy_kwh": 100.0, "carbon_kg": 45.0},
        "selected_bundle": {
            "bundle_id": "executor_test_bundle",
            "bundle_name": "executor_test_bundle",
            "original_bundle": {
                "bundle_id": "executor_test_bundle",
                "bundle_name": "executor_test_bundle",
                "goal": "reduce_energy_keep_comfort_safe",
                "event_type": "empty_room_detected",
                "actions": [APPROVED_ACTION],
            },
            "simulation_result": {
                "strategy_name": "eco_mode",
                "energy_saved_percent": 5.0,
                "carbon_reduced_percent": 5.0,
                "comfort_status": "Safe",
            },
        },
        "final_safety_approval": {
            "approved": execution_ready,
            "selected_bundle_id": "executor_test_bundle",
            "selected_bundle_name": "executor_test_bundle",
            "risk_level": "low",
            "safety_summary": "Approved one action for digital twin execution." if execution_ready else "Blocked by test.",
            "approved_actions": [APPROVED_ACTION] if execution_ready else [],
            "blocked_actions": [REJECTED_ACTION],
            "execution_ready": execution_ready,
            "execution_applied": False,
        },
    }


if __name__ == "__main__":
    blocked = execute_approved_bundle_in_digital_twin(plan(False))
    print(json.dumps(blocked, indent=2))
    assert blocked["execution_status"] == "blocked"
    assert blocked["execution_applied"] is False
    assert blocked["execution_scope"] == "energyplus_digital_twin_only"
    assert blocked["run_dir"] == ""

    bundle = build_execution_bundle_from_safety_approval(plan(True))
    assert bundle["actions"] == [APPROVED_ACTION]
    assert bundle["blocked_actions_not_executed"] == [REJECTED_ACTION]

    original_model = Path(energyplus_config.DEFAULT_MODEL)
    before_mtime = original_model.stat().st_mtime if original_model.exists() else None
    executed = execute_approved_bundle_in_digital_twin(plan(True))
    print(json.dumps(executed, indent=2))

    assert executed["execution_status"] in {"executed", "failed"}
    assert executed["execution_scope"] == "energyplus_digital_twin_only"
    assert executed["execution_applied"] == (executed["execution_status"] == "executed")
    assert executed["approved_actions_executed"] == [APPROVED_ACTION]
    assert REJECTED_ACTION not in executed["approved_actions_executed"]
    assert "executions" in executed["run_dir"]
    if before_mtime is not None:
        assert original_model.stat().st_mtime == before_mtime
    json.dumps(executed)

    print("\nPhase 5.4 digital twin executor test passed.")
