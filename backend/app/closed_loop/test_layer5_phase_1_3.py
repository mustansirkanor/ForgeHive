import json
import os
from pathlib import Path

from backend.app.closed_loop.layer5_api import run_layer5_phase_1_3_closed_loop
from backend.app.closed_loop.proof_export import export_layer5_phase_1_3_proof


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


def deterministic_bundles() -> list[dict]:
    return [
        {
            "bundle_id": "test_empty_room_bundle",
            "bundle_name": "test_empty_room_bundle",
            "goal": "reduce_energy_keep_comfort_safe",
            "event_type": "empty_room_detected",
            "actions": [
                {
                    "action_type": "lighting_adjustment",
                    "target": "unoccupied_zones",
                    "description": "Dim lights for empty room.",
                    "parameters": {"lighting_level_percent": 25},
                    "source": "test",
                    "confidence": 0.9,
                },
                {
                    "action_type": "hvac_setpoint_adjustment",
                    "target": "unoccupied_zones",
                    "description": "Relax cooling setpoint safely.",
                    "parameters": {"cooling_setpoint_c": 28},
                    "source": "test",
                    "confidence": 0.85,
                },
                {
                    "action_type": "ventilation_adjustment",
                    "target": "unoccupied_zones",
                    "description": "Reduce ventilation within safe bounds.",
                    "parameters": {"ventilation_percent": 40},
                    "source": "test",
                    "confidence": 0.8,
                },
            ],
            "rationale": "Test candidate for Layer 5 simulation.",
            "constraints": [],
            "expected_outcome": {"energy_saved_percent": 4, "comfort_impact": "neutral"},
            "created_by": "test",
            "requires_simulation": True,
            "fallback_used": False,
        }
    ]


if __name__ == "__main__":
    original = set_env({"FORGEHIVE_LLM_MODE": "mock"})
    try:
        plan = run_layer5_phase_1_3_closed_loop(
            "The meeting room is empty now. Save energy but keep comfort safe.",
            deterministic_bundles(),
            use_layer4_operator=False,
        )
        artifact_result = export_layer5_phase_1_3_proof(plan)
    finally:
        restore_env(original)

    print(json.dumps({
        "closed_loop_status": plan.get("closed_loop_status"),
        "candidate_count": plan.get("candidate_count"),
        "simulation_count": plan.get("simulation_count"),
        "successful_simulation_count": plan.get("successful_simulation_count"),
        "execution_ready": plan.get("execution_ready"),
        "execution_applied": plan.get("execution_applied"),
        "artifacts": artifact_result.get("generated_files"),
    }, indent=2))

    assert plan["candidate_count"] > 0
    assert plan["simulation_count"] > 0
    assert plan["ranked_bundles"] is not None
    if plan["successful_simulation_count"] > 0:
        assert plan["selected_bundle"] is not None
    assert plan["final_safety_approval"]
    assert plan["dashboard_summary"]["safetyGovernorUsed"] is True
    assert plan["dashboard_summary"]["rlBanditUsed"] is True
    assert plan["dashboard_summary"]["knowledgeGraphUsed"] is True
    assert plan["execution_applied"] is False
    assert plan["closed_loop_status"] in {"execution_ready_not_applied", "safe_no_action"}
    for path in artifact_result["generated_files"].values():
        assert Path(path).exists(), f"Missing artifact: {path}"

    print("\nPhase 5.1-5.3 test passed: Layer 5 can simulate, rank, and safety-approve candidate bundles without executing them.")
