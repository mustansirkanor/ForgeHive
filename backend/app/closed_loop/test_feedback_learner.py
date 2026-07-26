import json

from backend.app.closed_loop.feedback_learner import (
    generate_self_correction_recommendation,
    learn_from_execution,
)


SAFE_ACTION = {
    "action_id": "safe_lighting",
    "strategy_name": "eco_mode",
    "action_type": "lighting_adjustment",
    "target": "unoccupied_zones",
    "description": "Dim lights.",
    "parameters": {"lighting_level_percent": 25},
}


def plan() -> dict:
    return {
        "selected_bundle": {
            "bundle_id": "learning_safe_bundle",
            "bundle_name": "learning_safe_bundle",
            "total_score": 42.0,
            "original_bundle": {
                "bundle_id": "learning_safe_bundle",
                "bundle_name": "learning_safe_bundle",
                "goal": "reduce_energy_keep_comfort_safe",
                "event_type": "empty_room_detected",
                "actions": [
                    SAFE_ACTION,
                    {"action_type": "hvac_setpoint_adjustment", "parameters": {"cooling_setpoint_c": 28}},
                    {"action_type": "ventilation_adjustment", "parameters": {"ventilation_percent": 40}},
                ],
            },
            "simulation_result": {
                "energy_saved_percent": 6.0,
                "carbon_reduced_percent": 6.0,
                "comfort_status": "Safe",
            },
        },
        "final_safety_approval": {
            "execution_ready": True,
            "approved_actions": [SAFE_ACTION],
        },
    }


def execution(status: str = "executed", applied: bool = True, comfort: str = "Safe") -> dict:
    return {
        "phase": "5.4",
        "execution_status": status,
        "execution_applied": applied,
        "execution_scope": "energyplus_digital_twin_only",
        "selected_bundle_id": "learning_safe_bundle",
        "selected_bundle_name": "learning_safe_bundle",
        "approved_actions_executed": [SAFE_ACTION] if applied else [],
        "blocked_actions_not_executed": [],
        "run_dir": "runs/layer_5/executions/test_learning",
        "strategy_name": "eco_mode",
        "energy_saved_percent": 5.0 if applied else 0.0,
        "carbon_reduced_percent": 5.0 if applied else 0.0,
        "comfort_status": comfort,
        "anomaly_count": 0,
        "error": None if applied else "test failure",
    }


if __name__ == "__main__":
    failed = learn_from_execution(plan(), execution("failed", False, "Unknown"))
    print(json.dumps(failed, indent=2))
    assert failed["execution_success"] is False
    assert failed["bandit_updated"] is False
    assert failed["learning_status"] == "skipped"
    assert "safe no-action fallback" in failed["self_correction"]["summary"]

    successful = learn_from_execution(plan(), execution())
    print(json.dumps(successful, indent=2))
    assert successful["execution_success"] is True
    assert successful["expected_vs_actual"]["expected_energy_saved_percent"] == 6.0
    assert successful["expected_vs_actual"]["actual_energy_saved_percent"] == 5.0
    assert successful["actual_reward"] > 0
    assert successful["bandit_updated"] is True
    assert successful["memory_updated"] in {True, False}
    assert successful["knowledge_graph_updated"] in {True, False}
    assert successful["self_correction"]["recommendations"]

    regression_comparison = {
        "execution_success": True,
        "delta_energy_saving": 0,
        "delta_carbon_reduction": 0,
        "comfort_regression": True,
    }
    correction = generate_self_correction_recommendation(regression_comparison)
    assert "tighten comfort guardrails" in correction["summary"]

    print("\nPhase 5.5 feedback learner test passed.")
