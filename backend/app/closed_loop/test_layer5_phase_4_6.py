import json
from pathlib import Path

from backend.app.closed_loop.layer5_full_api import run_layer5_full_closed_loop


DETERMINISTIC_BUNDLE = {
    "bundle_id": "phase_5_4_6_deterministic_bundle",
    "bundle_name": "phase_5_4_6_deterministic_bundle",
    "goal": "reduce_energy_keep_comfort_safe",
    "event_type": "empty_room_detected",
    "actions": [
        {
            "action_type": "lighting_adjustment",
            "target": "unoccupied_zones",
            "description": "Dim lights in the empty room.",
            "parameters": {"lighting_level_percent": 25},
            "source": "test",
            "confidence": 0.9,
        },
        {
            "action_type": "hvac_setpoint_adjustment",
            "target": "unoccupied_zones",
            "description": "Relax cooling setpoint for the empty room.",
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
    "rationale": "Deterministic Layer 5 full-loop test bundle.",
    "constraints": [],
    "expected_outcome": {"energy_saved_percent": 4.0, "carbon_reduced_percent": 4.0, "comfort_impact": "neutral"},
    "created_by": "test",
    "requires_simulation": True,
    "fallback_used": False,
}


if __name__ == "__main__":
    output = run_layer5_full_closed_loop(
        user_message="The meeting room is empty now. Save energy but keep comfort safe.",
        candidate_bundles=[DETERMINISTIC_BUNDLE],
        use_layer4_operator=False,
    )

    print(json.dumps(output, indent=2))
    assert output["phase_5_1_3_plan"]
    assert output["phase_5_4_execution"]
    assert output["phase_5_5_learning"]
    assert output["phase_5_6_dashboard"]

    dashboard = output["phase_5_6_dashboard"]
    execution = output["phase_5_4_execution"]
    artifacts = output["artifact_paths"].get("generated_files", {})

    assert dashboard["safetyGovernorUsed"] is True
    assert dashboard["rlBanditUsed"] is True
    assert dashboard["knowledgeGraphUsed"] is True
    assert dashboard["energyPlusUsed"] is True
    assert dashboard["realBuildingExecutionEnabled"] is False
    assert dashboard["executionScope"] == "EnergyPlus digital twin only"
    assert execution["execution_scope"] == "energyplus_digital_twin_only"
    assert output["real_building_execution"] is False
    assert output["digital_twin_execution"] == (execution["execution_status"] == "executed")
    assert output["closed_loop_complete"] == (execution["execution_status"] == "executed")
    for path in artifacts.values():
        assert Path(path).exists()

    json.dumps(output)
    print("\nPhase 5.4-5.6 test passed: Layer 5 can execute in the digital twin, learn from feedback, and export closed-loop proof.")
