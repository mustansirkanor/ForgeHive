import json

from backend.app.cognitive.action_bundle_schema import validate_action_bundle
from backend.app.cognitive.llm_client import repair_provider_candidate_bundles


CONTEXT = {
    "goal": "reduce_energy_keep_comfort_safe",
    "event_type": "empty_room_detected",
}


def repair_payload(payload: dict) -> dict:
    raw_text = json.dumps(payload)
    return repair_provider_candidate_bundles(raw_text, "ollama", CONTEXT)


def assert_rejected(payload: dict, expected_text) -> None:
    try:
        repair_payload(payload)
    except ValueError as exc:
        message = str(exc)
        if isinstance(expected_text, (list, tuple, set)):
            assert any(text in message for text in expected_text), (
                f"Expected one of {expected_text!r} in {message!r}"
            )
        else:
            assert expected_text in message, f"Expected {expected_text!r} in {message!r}"
        return
    raise AssertionError("Expected payload to be rejected.")


def assert_first_bundle_valid(repair_result: dict) -> dict:
    bundle = repair_result["payload"]["candidate_bundles"][0]
    validation = validate_action_bundle(bundle)
    assert validation.valid, validation.errors
    return bundle


if __name__ == "__main__":
    repair_result = repair_payload(
        {
            "candidate_bundles": [
                {
                    "bundle_id": "ollama_empty_room_plan",
                    "actions": [
                        {
                            "action_type": "lighting_adjustment",
                            "action_value": 25,
                        }
                    ],
                }
            ]
        }
    )
    bundle = assert_first_bundle_valid(repair_result)
    action = bundle["actions"][0]

    assert bundle["bundle_name"] == "ollama_empty_room_plan"
    assert bundle["goal"] == "reduce_energy_keep_comfort_safe"
    assert bundle["event_type"] == "empty_room_detected"
    assert bundle["rationale"] == "Generated candidate bundle for simulation and safety review."
    assert bundle["constraints"] == []
    assert bundle["expected_outcome"] == {}
    assert bundle["created_by"] == "ollama_llm_candidate_generator"
    assert bundle["requires_simulation"] is True
    assert bundle["fallback_used"] is False
    assert isinstance(bundle["actions"], list)
    assert bundle["actions"]
    assert isinstance(bundle["expected_outcome"], dict)
    assert action["action_type"] == "lighting_adjustment"
    assert action["parameters"] == {"value": 25}
    assert action["target"] == "unoccupied_zones"
    description = action.get("description", "")
    assert isinstance(description, str)
    assert description.strip()
    assert len(description.strip()) >= 10
    assert action["source"] == "llm_generated"
    assert action["confidence"] == 0.65
    assert repair_result["schema_repair_applied"] is True
    assert repair_result["repair_notes"]

    recovered_action_result = repair_payload(
        {
            "candidate_bundles": [
                {
                    "bundle_name": "bundle_level_action",
                    "action_type": "hvac_setpoint_adjustment",
                    "action_value": 27,
                }
            ]
        }
    )
    recovered_bundle = assert_first_bundle_valid(recovered_action_result)
    assert len(recovered_bundle["actions"]) == 1
    assert recovered_bundle["actions"][0]["parameters"] == {"value": 27}

    complete_result = repair_payload(
        {
            "candidate_bundles": [
                {
                    "bundle_name": "already_valid",
                    "goal": "reduce_energy_keep_comfort_safe",
                    "event_type": "empty_room_detected",
                    "actions": [
                        {
                            "action_type": "ventilation_adjustment",
                            "target": "unoccupied_zones",
                            "description": "Reduce ventilation within safe candidate bounds.",
                            "parameters": {"ventilation_percent": 40},
                            "source": "llm_generated",
                            "confidence": 0.75,
                        }
                    ],
                    "rationale": "Already valid bundle.",
                    "constraints": [],
                    "expected_outcome": {},
                    "created_by": "ollama_llm_candidate_generator",
                    "requires_simulation": True,
                    "fallback_used": False,
                }
            ]
        }
    )
    assert_first_bundle_valid(complete_result)
    assert complete_result["schema_repair_applied"] is False

    assert_rejected({}, "candidate_bundles is missing or empty")
    assert_rejected({"candidate_bundles": []}, "candidate_bundles is missing or empty")
    assert_rejected(
        {
            "candidate_bundles": [
                {
                    "bundle_name": "empty_actions",
                    "actions": [],
                }
            ]
        },
        [
            "must contain a non-empty actions list",
            "No valid normalized candidate bundles remained",
            "no recoverable actions",
        ],
    )
    assert_rejected(
        {
            "candidate_bundles": [
                {
                    "bundle_name": "missing_action_type",
                    "actions": [{"target": "unoccupied_zones"}],
                }
            ]
        },
        [
            "action_type is not allowed",
            "unknown action_type",
            "all actions were unknown or invalid",
        ],
    )

    print("Phase 4.5.1 schema repair test passed.")
