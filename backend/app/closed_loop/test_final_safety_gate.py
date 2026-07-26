import json

from backend.app.closed_loop.final_safety_gate import run_final_safety_gate


SAFE_INTELLIGENCE = {
    "comfort": {"status": "Safe"},
    "building_state": {"occupancy": {"occupied_zones": 1}},
    "anomalies": {"highest_severity": "none", "anomalies": []},
}


def ranked(bundle: dict) -> dict:
    return {
        "bundle_id": bundle["bundle_id"],
        "bundle_name": bundle["bundle_name"],
        "simulation_result": {"strategy_name": "eco_mode"},
    }


def bundle_with_actions(actions: list[dict], name: str = "bundle") -> dict:
    return {
        "bundle_id": name,
        "bundle_name": name,
        "goal": "reduce_energy_keep_comfort_safe",
        "event_type": "empty_room_detected",
        "actions": actions,
        "expected_outcome": {"energy_saved_percent": 5, "comfort_impact": "neutral"},
    }


if __name__ == "__main__":
    safe_bundle = bundle_with_actions(
        [
            {
                "action_id": "safe_light",
                "action_type": "lighting_adjustment",
                "target": "unoccupied_zones",
                "description": "Dim unoccupied lights.",
                "parameters": {"lighting_level_percent": 25},
            }
        ],
        "safe_bundle",
    )
    safe_result = run_final_safety_gate(ranked(safe_bundle), safe_bundle, SAFE_INTELLIGENCE)

    unsafe_bundle = bundle_with_actions(
        [
            {
                "action_id": "unsafe_hvac",
                "action_type": "hvac_setpoint_adjustment",
                "target": "occupied_zones",
                "description": "Raise occupied cooling setpoint too high.",
                "parameters": {"cooling_setpoint_c": 30},
            }
        ],
        "unsafe_bundle",
    )
    unsafe_result = run_final_safety_gate(ranked(unsafe_bundle), unsafe_bundle, SAFE_INTELLIGENCE)

    all_rejected_bundle = bundle_with_actions(
        [
            {
                "action_id": "unsafe_hvac_1",
                "action_type": "hvac_setpoint_adjustment",
                "target": "occupied_zones",
                "description": "Raise occupied cooling setpoint too high.",
                "parameters": {"cooling_setpoint_c": 30},
            }
        ],
        "all_rejected_bundle",
    )
    all_rejected_result = run_final_safety_gate(ranked(all_rejected_bundle), all_rejected_bundle, SAFE_INTELLIGENCE)

    print(json.dumps({
        "safe_result": safe_result,
        "unsafe_result": unsafe_result,
        "all_rejected_result": all_rejected_result,
    }, indent=2))

    assert safe_result["execution_ready"] is True
    assert safe_result["execution_applied"] is False
    assert unsafe_result["execution_ready"] is False
    assert unsafe_result["blocked_actions"]
    assert all_rejected_result["execution_ready"] is False
    assert all_rejected_result["approved_actions"] == []
    assert all_rejected_result["safety_decisions"]

    print("\nPhase 5.3 final safety gate test passed.")
