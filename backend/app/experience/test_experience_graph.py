import json

from backend.app.experience.experience_api import record_experience_after_execution
from backend.app.experience.experience_ranker import apply_experience_prior_to_candidate_bundles
from backend.app.experience.experience_retriever import retrieve_similar_experiences
from backend.app.experience.experience_store import append_experience_episode, get_failure_patterns, load_experience_graph
from backend.app.experience.llm_context_builder import build_experience_context_for_llm
from backend.app.experience.seed_experiences import seed_demo_experiences
from backend.app.experience.similarity import calculate_situation_similarity


def fake_episode() -> dict:
    return {
        "experience_id": "exp_test_append",
        "created_at": "2026-07-25T15:00:00+00:00",
        "situation": {
            "event_type": "empty_room_detected",
            "goal": "reduce_energy_keep_comfort_safe",
            "occupancy": 0,
            "temperature_c": 24,
            "co2_ppm": 650,
            "carbon_state": "high",
            "next_meeting_minutes": 90,
            "comfort_status": "Safe",
            "anomaly_count": 0,
            "timestamp": "2026-07-25T15:00:00+00:00",
        },
        "candidate_plans": [
            {
                "bundle_id": "test_balanced",
                "bundle_name": "balanced_empty_room_mode",
                "action_types": ["lighting_adjustment", "hvac_setpoint_adjustment", "ventilation_adjustment"],
                "actions": [],
                "simulated_energy_saved_percent": 12,
                "simulated_carbon_reduced_percent": 10,
                "simulated_comfort_status": "Safe",
                "simulation_success": True,
                "rank": 1,
                "score": 45,
                "reward": 45,
                "safety_status": "approved",
                "blocked": False,
            }
        ],
        "selected_plan": {"bundle_name": "balanced_empty_room_mode", "reward": 45},
        "approved_actions": [],
        "blocked_actions": [],
        "execution_outcome": {
            "execution_status": "executed",
            "energy_saved_percent": 12,
            "carbon_reduced_percent": 10,
            "comfort_status": "Safe",
            "anomaly_count": 0,
            "reward": 45,
            "bandit_updated": True,
            "memory_updated": True,
            "knowledge_graph_updated": True,
            "real_building_execution": False,
            "digital_twin_execution": True,
        },
        "lessons_learned": ["Balanced empty-room strategy preserved comfort and saved energy."],
        "confidence": 0.92,
        "tags": ["empty_room"],
        "source": "test",
    }


if __name__ == "__main__":
    seed_result = seed_demo_experiences(force=True)
    assert seed_result["episode_count"] >= 5

    append_result = append_experience_episode(fake_episode())
    assert append_result["experience_graph_updated"] is True
    assert load_experience_graph()["episodes"]

    current = {
        "event_type": "empty_room_detected",
        "goal": "reduce_energy_keep_comfort_safe",
        "occupancy": 0,
        "temperature_c": 24,
        "co2_ppm": 650,
        "carbon_state": "high",
        "next_meeting_minutes": 90,
        "comfort_status": "Safe",
        "anomaly_count": 0,
    }
    retrieved = retrieve_similar_experiences(current)
    assert retrieved["similar_experiences_found"] > 0
    assert retrieved["historical_recommendation"]["preferred_plan"]

    assert get_failure_patterns()
    assert any(pattern["action_type"] == "hvac_shutdown" for pattern in get_failure_patterns())
    score = calculate_situation_similarity(current, retrieved["top_matches"][0] and load_experience_graph()["episodes"][0]["situation"])
    assert 0 <= score <= 1

    context = build_experience_context_for_llm(retrieved)
    assert "balanced_empty_room_mode" in context
    assert "Failed pattern" in context
    assert "Safety Governor remains final authority" in context

    bundles = [
        {
            "bundle_name": "balanced_empty_room_mode",
            "actions": [
                {"action_type": "lighting_adjustment"},
                {"action_type": "hvac_setpoint_adjustment"},
                {"action_type": "ventilation_adjustment"},
            ],
        },
        {"bundle_name": "aggressive_shutdown", "actions": [{"action_type": "hvac_shutdown"}]},
    ]
    prior = apply_experience_prior_to_candidate_bundles(bundles, retrieved)
    by_name = {bundle["bundle_name"]: bundle for bundle in prior["candidate_bundles"]}
    assert by_name["balanced_empty_room_mode"]["experience_prior_score"] > 0
    assert by_name["aggressive_shutdown"]["experience_prior_score"] < 0

    fake_plan = {
        "layer4_intent": {"goal": "reduce_energy_keep_comfort_safe", "event_type": "empty_room_detected"},
        "ranked_bundles": [
            {
                "rank": 1,
                "bundle_id": "safe",
                "bundle_name": "balanced_empty_room_mode",
                "final_score": 50,
                "base_reward_score": 45,
                "original_bundle": bundles[0],
                "simulation_result": {
                    "simulation_status": "success",
                    "energy_saved_percent": 12,
                    "carbon_reduced_percent": 10,
                    "comfort_status": "Safe",
                },
            }
        ],
        "selected_bundle": {
            "rank": 1,
            "bundle_id": "safe",
            "bundle_name": "balanced_empty_room_mode",
            "final_score": 50,
            "base_reward_score": 45,
            "original_bundle": bundles[0],
            "simulation_result": {
                "simulation_status": "success",
                "energy_saved_percent": 12,
                "carbon_reduced_percent": 10,
                "comfort_status": "Safe",
            },
        },
        "final_safety_approval": {"approved_actions": bundles[0]["actions"], "blocked_actions": []},
        "experience_prior_summary": {"similar_experiences_found": retrieved["similar_experiences_found"]},
    }
    fake_execution = {
        "execution_status": "executed",
        "execution_applied": True,
        "energy_saved_percent": 12,
        "carbon_reduced_percent": 10,
        "comfort_status": "Safe",
        "anomaly_count": 0,
    }
    fake_learning = {"actual_reward": 45, "bandit_updated": True, "memory_updated": True, "knowledge_graph_updated": True}
    update = record_experience_after_execution(fake_plan, fake_execution, fake_learning)
    assert update["experience_graph_updated"] is True
    assert update["real_building_execution"] is False

    print(json.dumps({"total_tests": 10, "passed_tests": 10, "failed_tests": 0}, indent=2))
