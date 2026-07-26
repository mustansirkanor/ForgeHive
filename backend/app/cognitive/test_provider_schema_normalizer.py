from backend.app.cognitive.action_bundle_schema import validate_action_bundle
from backend.app.cognitive.provider_schema_normalizer import normalize_llm_candidate_response


GOAL = "reduce_energy_keep_comfort_safe"
EVENT_TYPE = "empty_room_detected"


def normalize(payload: dict) -> dict:
    return normalize_llm_candidate_response(payload, "test_provider", GOAL, EVENT_TYPE)


def first_bundle(result: dict) -> dict:
    return result["normalized_response"]["candidate_bundles"][0]


def assert_repaired_bundle_valid(result: dict) -> dict:
    bundle = first_bundle(result)
    validation = validate_action_bundle(bundle)
    assert validation.valid, validation.errors
    return bundle


def one_action_payload(action_type: str, expected_outcome=None) -> dict:
    payload = {
        "candidate_bundles": [
            {
                "id": "test_bundle",
                "actions": [{"action_type": action_type, "value": 25}],
                "expected_outcome": expected_outcome,
                "constraints": "candidate only",
            }
        ]
    }
    return payload


if __name__ == "__main__":
    string_result = normalize(one_action_payload("lighting_control", "saves energy"))
    bundle = assert_repaired_bundle_valid(string_result)
    assert bundle["expected_outcome"] == {"summary": "saves energy"}
    assert bundle["constraints"] == ["candidate only"]
    assert bundle["actions"][0]["action_type"] == "lighting_adjustment"

    number_result = normalize(one_action_payload("hvac_adjustment", 4.2))
    bundle = assert_repaired_bundle_valid(number_result)
    assert bundle["expected_outcome"] == {"estimated_value": 4.2}
    assert bundle["actions"][0]["action_type"] == "hvac_setpoint_adjustment"

    list_result = normalize(one_action_payload("iaq_control", ["comfort neutral"]))
    bundle = assert_repaired_bundle_valid(list_result)
    assert bundle["expected_outcome"] == {"items": ["comfort neutral"]}
    assert bundle["actions"][0]["action_type"] == "ventilation_adjustment"

    alias_payload = {
        "candidate_bundles": [
            {
                "name": "alias_bundle",
                "actions": [
                    {"action_type": "occupancy_based_control"},
                    {"action_type": "lighting_control"},
                    {"action_type": "hvac_adjustment"},
                    {"action_type": "iaq_control"},
                    {"action_type": "carbon_shift"},
                    {"action_type": "mystery_control"},
                ],
            }
        ]
    }
    alias_result = normalize(alias_payload)
    bundle = assert_repaired_bundle_valid(alias_result)
    action_types = [action["action_type"] for action in bundle["actions"]]
    assert action_types == [
        "strategy_mode",
        "lighting_adjustment",
        "hvac_setpoint_adjustment",
        "ventilation_adjustment",
        "carbon_schedule_shift",
    ]
    assert len(alias_result["dropped_actions"]) == 1

    partial_result = normalize(
        {
            "candidate_bundles": [
                {
                    "bundle_name": "partial_bundle",
                    "actions": [
                        {"action_type": "unknown_action"},
                        {"action_type": "dim_lights"},
                    ],
                }
            ]
        }
    )
    bundle = assert_repaired_bundle_valid(partial_result)
    assert bundle["actions"][0]["action_type"] == "lighting_adjustment"
    assert len(partial_result["dropped_actions"]) == 1
    assert partial_result["normalized_bundle_count"] == 1

    all_unknown_result = normalize(
        {
            "candidate_bundles": [
                {
                    "bundle_name": "bad_bundle",
                    "actions": [{"action_type": "unknown_action"}],
                }
            ]
        }
    )
    assert all_unknown_result["normalized_bundle_count"] == 0
    assert len(all_unknown_result["dropped_bundles"]) == 1

    no_valid_result = normalize({"candidate_bundles": []})
    assert no_valid_result["normalized_bundle_count"] == 0
    assert no_valid_result["normalized_response"]["candidate_bundles"] == []

    print("Phase 4.6.1 provider schema normalizer test passed.")
