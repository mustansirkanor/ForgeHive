import json

from backend.app.closed_loop.reward_ranker import rank_simulated_bundles
from backend.app.closed_loop.schemas import to_jsonable
from backend.app.experience.experience_retriever import retrieve_similar_experiences
from backend.app.experience.seed_experiences import seed_demo_experiences


SAFE_BUNDLE = {
    "bundle_id": "safe_bundle",
    "bundle_name": "safe_bundle",
    "goal": "reduce_energy_keep_comfort_safe",
    "event_type": "empty_room_detected",
    "actions": [
        {"action_type": "lighting_adjustment", "parameters": {"lighting_level_percent": 25}},
        {"action_type": "hvac_setpoint_adjustment", "parameters": {"cooling_setpoint_c": 28}},
    ],
}

FAILED_BUNDLE = {
    "bundle_id": "failed_bundle",
    "bundle_name": "failed_bundle",
    "goal": "reduce_energy_keep_comfort_safe",
    "event_type": "empty_room_detected",
    "actions": [{"action_type": "lighting_adjustment", "parameters": {"lighting_level_percent": 25}}],
}

UNSAFE_BUNDLE = {
    "bundle_id": "unsafe_bundle",
    "bundle_name": "unsafe_bundle",
    "goal": "reduce_energy_keep_comfort_safe",
    "event_type": "empty_room_detected",
    "actions": [{"action_type": "hvac_setpoint_adjustment", "parameters": {"cooling_setpoint_c": 30}}],
}


def simulation(bundle: dict, status: str, comfort: str, energy_saved: float) -> dict:
    return {
        "bundle_id": bundle["bundle_id"],
        "bundle_name": bundle["bundle_name"],
        "simulation_status": status,
        "energy_saved_percent": energy_saved,
        "carbon_reduced_percent": energy_saved,
        "comfort_status": comfort,
        "comfort_violation_minutes": 0,
        "anomaly_count": 0,
        "actions_simulated": bundle["actions"],
    }


if __name__ == "__main__":
    seed_demo_experiences(force=True)
    retrieved = retrieve_similar_experiences(
        {
            "event_type": "empty_room_detected",
            "goal": "reduce_energy_keep_comfort_safe",
            "occupancy": 0,
            "comfort_status": "Safe",
            "carbon_state": "high",
            "co2_ppm": 650,
            "next_meeting_minutes": 90,
            "anomaly_count": 0,
        }
    )
    output = rank_simulated_bundles(
        [
            simulation(FAILED_BUNDLE, "failed", "Unknown", 99),
            simulation(UNSAFE_BUNDLE, "success", "Unsafe", 99),
            simulation(SAFE_BUNDLE, "success", "Safe", 5),
        ],
        [SAFE_BUNDLE, FAILED_BUNDLE, UNSAFE_BUNDLE],
        "reduce_energy_keep_comfort_safe",
        "empty_room_detected",
        retrieved,
    )

    print(json.dumps(to_jsonable(output), indent=2))
    assert output["ranked_bundles"]
    assert output["selected_bundle"] is not None
    assert output["selected_bundle"]["bundle_id"] == "safe_bundle"
    ranked_by_id = {bundle["bundle_id"]: bundle for bundle in output["ranked_bundles"]}
    assert ranked_by_id["safe_bundle"]["rank"] == 1
    assert ranked_by_id["unsafe_bundle"]["total_score"] < ranked_by_id["safe_bundle"]["total_score"]
    assert ranked_by_id["failed_bundle"]["total_score"] < ranked_by_id["safe_bundle"]["total_score"]
    assert ranked_by_id["unsafe_bundle"]["penalty_reasons"]
    assert ranked_by_id["failed_bundle"]["penalty_reasons"]
    assert ranked_by_id["unsafe_bundle"]["final_penalty"] <= -100
    assert ranked_by_id["failed_bundle"]["final_penalty"] <= -100
    assert output["ranked_bundles"][0]["bandit_prior_score"] is not None
    assert output["ranked_bundles"][0]["kg_relevance_score"] is not None
    assert output["ranked_bundles"][0]["experience_prior_score"] is not None
    assert output["ranked_bundles"][0]["base_reward_score"] is not None
    assert output["ranked_bundles"][0]["final_score"] == output["ranked_bundles"][0]["total_score"]
    assert output["experience_prior_used"] is True
    assert output["experience_prior_summary"]["similar_experiences_found"] > 0
    assert output["rl_used"] is True
    assert output["kg_used"] is True
    json.dumps(to_jsonable(output))

    print("\nPhase 5.2 reward ranker test passed.")
