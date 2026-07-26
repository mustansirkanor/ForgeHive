import json
import re

from backend.app.demo_api.artifact_loader import build_final_summary, build_frontend_demo_response, list_artifacts, load_artifact_bundle
from backend.app.demo_api.scenarios import get_scenarios
from backend.app.demo_api.server import health, run_demo_message, run_demo_scenario
from backend.app.experience.experience_api import get_experience_memory_summary, query_experience_memory
from backend.app.cognitive.operator_intents import classify_operator_intent
from backend.app.cognitive.request_semantics import bundle_semantic_violations
from backend.app.cognitive.candidate_bundle_generator import (
    build_candidate_generation_prompt,
    compose_complete_llm_bundles,
    deduplicate_valid_bundles,
    normalize_llm_bundle,
)
from backend.app.closed_loop.final_safety_gate import run_final_safety_gate
from backend.app.closed_loop.reward_ranker import get_kg_relevance_score


def assert_no_secrets(payload: object) -> None:
    text = json.dumps(payload)
    forbidden = [
        "OPENROUTER_API_KEY",
        r"sk-or-[A-Za-z0-9_\-]{10,}",
        r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]",
    ]
    for pattern in forbidden:
        assert not re.search(pattern, text), f"secret-like value leaked: {pattern}"


def test_health() -> None:
    payload = health()
    assert payload["status"] == "ok"
    assert payload["realBuildingExecution"] is False
    assert_no_secrets(payload)


def test_final_summary() -> None:
    payload = build_final_summary()
    assert payload["readinessScore"] >= 100
    assert payload["grade"] == "Excellent"
    assert payload["judgeReady"] is True
    assert payload["realBuildingExecution"] is False
    assert_no_secrets(payload)


def test_scenarios() -> None:
    ids = {scenario["id"] for scenario in get_scenarios()}
    assert {"empty_room", "high_co2", "high_carbon", "too_hot", "unsafe_command"} <= ids


def test_run_artifact_mode_normalized() -> None:
    payload = run_demo_scenario("empty_room", "artifact")
    assert payload["project"] == "ForgeHive"
    assert payload["mode"] == "artifact"
    assert payload["pipeline"]
    assert payload["candidateBundles"]
    assert payload["experienceGraph"]["enabled"] is True
    assert payload["experienceGraph"]["similarExperiencesFound"] >= 1
    assert_no_secrets(payload)


def test_empty_room_never_real_building() -> None:
    payload = run_demo_scenario("empty_room", "artifact")
    assert payload["digitalTwin"]["realBuildingExecution"] is False


def test_unsafe_command_rejected() -> None:
    payload = run_demo_scenario("unsafe_command", "artifact")
    assert payload["safety"]["approved"] is False
    assert payload["safety"]["blockedActions"]
    assert payload["digitalTwin"]["realBuildingExecution"] is False
    assert any(step["status"] == "rejected" for step in payload["pipeline"])


def test_operator_ask_artifact_mode() -> None:
    payload = run_demo_message("The meeting room is empty now. Save energy but keep comfort safe.", "artifact")
    assert payload["project"] == "ForgeHive"
    assert payload["userMessage"]
    assert payload["digitalTwin"]["realBuildingExecution"] is False
    assert payload["experienceGraph"]["enabled"] is True
    assert_no_secrets(payload)


def test_experience_memory_endpoint_payload() -> None:
    payload = get_experience_memory_summary()
    assert payload["experienceGraphEnabled"] is True
    assert payload["totalExperiences"] >= 5
    assert payload["topStrategies"]
    assert_no_secrets(payload)


def test_experience_query_endpoint_payload() -> None:
    payload = query_experience_memory(
        {
            "event_type": "empty_room_detected",
            "goal": "reduce_energy_keep_comfort_safe",
            "building_state": {
                "occupancy": 0,
                "temperature_c": 24,
                "co2_ppm": 650,
                "carbon_state": "high",
                "next_meeting_minutes": 90,
            },
        }
    )
    assert payload["similar_experiences_found"] >= 1
    assert payload["historical_recommendation"]["preferred_plan"]
    assert_no_secrets(payload)


def test_empty_room_request_uses_unoccupied_energy_actions() -> None:
    payload = run_demo_message("The meeting has ended and the room is empty", "artifact")
    action_types = {action["actionType"] for action in payload["safety"]["approvedActions"]}
    targets = {action["target"] for action in payload["safety"]["approvedActions"]}
    assert payload["detectedIntents"] == ["empty_room"]
    assert action_types == {"lighting_adjustment", "hvac_setpoint_adjustment", "ventilation_adjustment"}
    assert all("unoccupied" in target for target in targets)
    assert payload["selectedBundle"]["name"] == "empty_room_energy_save_bundle"
    assert "occupied" not in payload["selectedBundle"]["name"]


def test_empty_room_semantics_allow_unoccupied_targets_only() -> None:
    intent = classify_operator_intent("The meeting has ended and the room is empty")
    analysis = intent["request_analysis"]
    valid_bundle = {
        "actions": [
            {"action_type": "lighting_adjustment", "target": "unoccupied_zones", "parameters": {"lighting_level_percent": 25}},
            {"action_type": "hvac_setpoint_adjustment", "target": "unoccupied_zones", "parameters": {"cooling_setpoint_c": 28}},
            {"action_type": "ventilation_adjustment", "target": "unoccupied_zones", "parameters": {"ventilation_percent": 40}},
        ]
    }
    invalid_bundle = {
        "actions": [
            {"action_type": "lighting_adjustment", "target": "occupied_zones", "parameters": {"lighting_level_percent": 25}},
            {"action_type": "hvac_setpoint_adjustment", "target": "occupied_zones", "parameters": {"cooling_setpoint_c": 24}},
            {"action_type": "ventilation_adjustment", "target": "occupied_zones", "parameters": {"ventilation_percent": 40}},
        ]
    }
    assert bundle_semantic_violations(valid_bundle, analysis) == []
    assert any("targets occupied zones" in violation for violation in bundle_semantic_violations(invalid_bundle, analysis))


def test_empty_room_with_future_meeting_schedules_recovery() -> None:
    message = "The meeting has ended and the room is empty and their meeting in next 90 mins so we want the best for both the situation"
    intent = classify_operator_intent(message)
    assert intent["request_analysis"]["next_meeting_minutes"] == 90
    payload = run_demo_message(message, "artifact")
    action_types = {action["actionType"] for action in payload["safety"]["approvedActions"]}
    assert "preconditioning_schedule" in action_types
    recovery = next(action for action in payload["safety"]["approvedActions"] if action["actionType"] == "preconditioning_schedule")
    assert recovery["parameters"]["next_meeting_minutes"] == 90
    assert recovery["parameters"]["restore_minutes_before_meeting"] == 20


def test_operator_compound_request_creates_multiple_actions() -> None:
    payload = run_demo_message(
        "The meeting room is very hot. Improve comfort and dim the lights.",
        "artifact",
    )
    action_types = {action["actionType"] for action in payload["safety"]["approvedActions"]}
    assert payload["detectedIntents"] == ["too_hot", "dim_lights"]
    assert action_types == {"hvac_setpoint_adjustment", "lighting_adjustment"}
    assert payload["selectedBundle"]["name"] == "multi_intent_hot_dim_lights_bundle"
    assert payload["digitalTwin"]["energySavedPercent"] != 4.8
    assert payload["idfAdapter"]["hvacSetpointAppliedInIDF"] is True
    assert payload["idfAdapter"]["lightingAppliedInIDF"] is True
    assert payload["idfAdapter"]["ventilationAppliedInIDF"] is False
    assert payload["digitalTwin"]["realBuildingExecution"] is False
    assert_no_secrets(payload)


def test_live_response_preserves_real_closed_loop_selection() -> None:
    artifacts = load_artifact_bundle()
    real_result = artifacts["layer57"]
    payload = build_frontend_demo_response(
        raw={"layer57": real_result},
        user_message=real_result.get("user_message", "live request"),
        mode="live",
    )
    actual_selected = real_result["layer5_result"]["phase_5_1_3_plan"]["selected_bundle"]["bundle_name"]
    assert payload["selectedBundle"]["name"] == actual_selected
    assert payload["provider"]["selectedProvider"] == real_result["selected_provider"]
    assert payload["rankedCandidates"]
    assert payload["explanationSteps"]
    assert payload["digitalTwin"]["realBuildingExecution"] is False
    assert_no_secrets(payload)


def test_occupied_multi_issue_request_semantics() -> None:
    message = "Temperature is high, it is suffocating in the meeting room, and the lighting is poor."
    intent = classify_operator_intent(message)
    analysis = intent["request_analysis"]
    assert intent["intent"] == "multi_objective_control"
    assert analysis["occupancy"] == "occupied"
    assert set(analysis["issues"]) == {"high_temperature", "poor_air_quality", "insufficient_lighting"}

    wrong_bundle = {
        "actions": [
            {
                "action_type": "lighting_adjustment",
                "target": "unoccupied_zones",
                "description": "Dim lights.",
                "parameters": {"lighting_level_percent": 25},
            },
            {
                "action_type": "hvac_setpoint_adjustment",
                "target": "unoccupied_zones",
                "description": "Relax cooling.",
                "parameters": {"cooling_setpoint_c": 28},
            },
        ]
    }
    violations = bundle_semantic_violations(wrong_bundle, analysis)
    assert any("missing required ventilation_adjustment" in violation for violation in violations)
    assert any("unoccupied" in violation for violation in violations)
    assert any("dims lighting" in violation for violation in violations)


def test_safety_gate_blocks_action_opposite_to_request() -> None:
    analysis = classify_operator_intent(
        "Temperature is high and it is suffocating in the occupied meeting room with poor light."
    )["request_analysis"]
    original = {
        "bundle_id": "contradictory",
        "bundle_name": "contradictory",
        "expected_outcome": {},
        "actions": [
            {
                "action_type": "lighting_adjustment",
                "target": "unoccupied_zones",
                "description": "Dim lights.",
                "parameters": {"lighting_level_percent": 25},
            }
        ],
    }
    selected = {"simulation_result": {"strategy_name": "eco_mode"}}
    approval = run_final_safety_gate(selected, original, {"request_analysis": analysis})
    assert approval["approved"] is False
    assert approval["blocked_actions"]
    assert approval["blocked_actions"][0]["decision"]["blocked_by"] == ["operator_request_semantics"]


def test_multi_issue_prompt_requires_every_action_type() -> None:
    message = "Temperature is high, it is suffocating in the meeting room, and lighting is poor."
    analysis = classify_operator_intent(message)["request_analysis"]
    prompt = build_candidate_generation_prompt({
        "goal": "resolve_occupied_multi_issue",
        "event_type": "occupied_multi_issue_detected",
        "building_context": {},
        "knowledge_context": {},
        "constraints": [],
        "extra_context": {
            "operator_request": message,
            "request_analysis": analysis,
            "required_outcomes": analysis["requirements"],
        },
    })
    assert '"hvac_setpoint_adjustment"' in prompt
    assert '"ventilation_adjustment"' in prompt
    assert '"lighting_adjustment"' in prompt
    assert "Required target for request-specific control actions: occupied_zones" in prompt


def test_llm_partial_plans_are_composed_without_inventing_actions() -> None:
    message = "The occupied meeting room is hot, suffocating, and has poor lighting."
    analysis = classify_operator_intent(message)["request_analysis"]
    context = {
        "goal": "resolve_occupied_multi_issue",
        "event_type": "occupied_multi_issue_detected",
        "constraints": [],
        "extra_context": {"request_analysis": analysis},
    }
    raw_bundles = [
        {
            "bundle_name": "llm_air_and_light",
            "actions": [
                {"action_type": "ventilation_adjustment", "target": "occupied_zones", "description": "Increase fresh air.", "parameters": {"ventilation_multiplier": 1.2}, "confidence": 0.8},
                {"action_type": "lighting_adjustment", "target": "occupied_zones", "description": "Increase lighting.", "parameters": {"lighting_level_percent": 75}, "confidence": 0.8},
            ],
        },
        {
            "bundle_name": "llm_cooling",
            "actions": [
                {"action_type": "hvac_setpoint_adjustment", "target": "occupied_zones", "description": "Increase cooling.", "parameters": {"cooling_setpoint_c": 24}, "confidence": 0.8},
            ],
        },
    ]
    normalized = [normalize_llm_bundle(bundle, context["goal"], context["event_type"]) for bundle in raw_bundles]
    composed = compose_complete_llm_bundles(normalized, context)
    assert composed
    composed_dict = composed[0]
    assert composed_dict.created_by == "llm_plan_composer"
    assert composed_dict.fallback_used is False
    assert {action.action_type for action in composed_dict.actions} == {
        "hvac_setpoint_adjustment",
        "ventilation_adjustment",
        "lighting_adjustment",
    }


def test_stuffy_room_requires_an_increase_multiplier() -> None:
    analysis = classify_operator_intent("The occupied meeting room is stuffy.")["request_analysis"]
    ambiguous_percent = {
        "actions": [{
            "action_type": "ventilation_adjustment",
            "target": "occupied_zones",
            "description": "Increase fresh air.",
            "parameters": {"ventilation_percent": 70},
        }]
    }
    safe_increase = {
        "actions": [{
            "action_type": "ventilation_adjustment",
            "target": "occupied_zones",
            "description": "Increase fresh air.",
            "parameters": {"ventilation_multiplier": 1.2},
        }]
    }
    assert any("ventilation_multiplier" in item for item in bundle_semantic_violations(ambiguous_percent, analysis))
    assert bundle_semantic_violations(safe_increase, analysis) == []


def test_occupied_cooling_respects_model_deadband_floor() -> None:
    analysis = classify_operator_intent("The occupied meeting room is hot.")["request_analysis"]
    unsafe = {
        "actions": [{
            "action_type": "hvac_setpoint_adjustment",
            "target": "occupied_zones",
            "description": "Cool the room.",
            "parameters": {"cooling_setpoint_c": 22},
        }]
    }
    assert any("23C" in item for item in bundle_semantic_violations(unsafe, analysis))


def test_identical_candidate_controls_are_not_counted_twice() -> None:
    actions = [{
        "action_type": "lighting_adjustment",
        "target": "occupied_zones",
        "parameters": {"lighting_level_percent": 70},
    }]
    validation = deduplicate_valid_bundles({
        "valid_bundles": [
            {"bundle_name": "plan_a", "actions": actions},
            {"bundle_name": "plan_b", "actions": actions},
        ]
    })
    assert len(validation["valid_bundles"]) == 1


def test_composite_request_gets_knowledge_graph_relevance() -> None:
    bundle = {
        "goal": "resolve_occupied_comfort_iaq_lighting",
        "event_type": "occupied_multi_issue_detected",
        "actions": [
            {"action_type": "hvac_setpoint_adjustment", "parameters": {}},
            {"action_type": "ventilation_adjustment", "parameters": {}},
            {"action_type": "lighting_adjustment", "parameters": {}},
        ],
    }
    result = get_kg_relevance_score(bundle, bundle["goal"], bundle["event_type"])
    assert result["score"] > 0
    assert set(result["matched_actions"]) == {
        "hvac_setpoint_adjustment",
        "ventilation_adjustment",
        "lighting_adjustment",
    }


def test_artifacts_list() -> None:
    payload = list_artifacts()
    names = {artifact["name"] for artifact in payload["artifacts"]}
    assert "forgehive_final_audit.json" in names
    assert "layer5_7_real_ollama_full_loop.json" in names
    assert payload["realBuildingExecution"] is False
    assert_no_secrets(payload)


def run_tests() -> None:
    tests = [
        test_health,
        test_final_summary,
        test_scenarios,
        test_run_artifact_mode_normalized,
        test_empty_room_never_real_building,
        test_unsafe_command_rejected,
        test_operator_ask_artifact_mode,
        test_experience_memory_endpoint_payload,
        test_experience_query_endpoint_payload,
        test_empty_room_request_uses_unoccupied_energy_actions,
        test_empty_room_semantics_allow_unoccupied_targets_only,
        test_empty_room_with_future_meeting_schedules_recovery,
        test_operator_compound_request_creates_multiple_actions,
        test_live_response_preserves_real_closed_loop_selection,
        test_occupied_multi_issue_request_semantics,
        test_safety_gate_blocks_action_opposite_to_request,
        test_multi_issue_prompt_requires_every_action_type,
        test_llm_partial_plans_are_composed_without_inventing_actions,
        test_stuffy_room_requires_an_increase_multiplier,
        test_occupied_cooling_respects_model_deadband_floor,
        test_identical_candidate_controls_are_not_counted_twice,
        test_composite_request_gets_knowledge_graph_relevance,
        test_artifacts_list,
    ]
    for test in tests:
        test()
    print(json.dumps({"total_tests": len(tests), "passed_tests": len(tests), "failed_tests": 0}, indent=2))


if __name__ == "__main__":
    run_tests()
