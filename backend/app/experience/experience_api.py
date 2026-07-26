from datetime import datetime, timezone

from backend.app.experience.experience_retriever import retrieve_similar_experiences
from backend.app.experience.experience_store import append_experience_episode, summarize_experience_memory
from backend.app.experience.seed_experiences import seed_demo_experiences
from backend.app.experience.similarity import extract_situation_signature_from_context


def get_experience_memory_summary() -> dict:
    seed_demo_experiences(force=False)
    return summarize_experience_memory()


def query_experience_memory(payload: dict) -> dict:
    seed_demo_experiences(force=False)
    context = {
        "event_type": payload.get("event_type"),
        "goal": payload.get("goal"),
        "building_state": payload.get("building_state", {}),
        **(payload.get("building_state", {}) if isinstance(payload.get("building_state"), dict) else {}),
    }
    return retrieve_similar_experiences(extract_situation_signature_from_context(context))


def candidate_experience_from_ranked(ranked: dict) -> dict:
    original = ranked.get("original_bundle") or {}
    simulation = ranked.get("simulation_result") or {}
    actions = original.get("actions") or simulation.get("actions_simulated") or []
    return {
        "bundle_id": ranked.get("bundle_id") or original.get("bundle_id"),
        "bundle_name": ranked.get("bundle_name") or original.get("bundle_name"),
        "action_types": list(dict.fromkeys(action.get("action_type") for action in actions if action.get("action_type"))),
        "actions": actions,
        "simulated_energy_saved_percent": simulation.get("energy_saved_percent"),
        "simulated_carbon_reduced_percent": simulation.get("carbon_reduced_percent"),
        "simulated_comfort_status": simulation.get("comfort_status"),
        "simulation_success": simulation.get("simulation_status") == "success",
        "rank": ranked.get("rank"),
        "score": ranked.get("final_score", ranked.get("total_score")),
        "reward": ranked.get("base_reward_score", ranked.get("reward_score")),
        "safety_status": "approved",
        "blocked": bool(ranked.get("final_penalty", 0) <= -100 or simulation.get("comfort_status") == "Unsafe"),
    }


def lessons_from_execution(plan: dict, execution_result: dict, learning_report: dict) -> list[str]:
    selected = plan.get("selected_bundle") or {}
    selected_name = selected.get("bundle_name", "selected plan")
    comfort = execution_result.get("comfort_status", "Unknown")
    reward = learning_report.get("actual_reward", selected.get("reward_score"))
    lessons = []
    if execution_result.get("execution_status") == "executed" and comfort == "Safe":
        lessons.append(f"{selected_name} preserved comfort and produced reward {reward}.")
    if execution_result.get("blocked_actions_not_executed"):
        lessons.append("Safety Governor blocked risky actions before digital-twin execution.")
    if selected.get("experience_prior_score"):
        lessons.append("Historical experience prior helped bias ranking toward a previously successful pattern.")
    if not lessons:
        lessons.append("Outcome recorded for future similar building situations.")
    return lessons


def record_experience_after_execution(plan_5_1_3: dict, execution_result: dict, learning_report: dict) -> dict:
    situation = extract_situation_signature_from_context(
        {
            "goal": (plan_5_1_3.get("layer4_intent") or {}).get("goal"),
            "event_type": (plan_5_1_3.get("layer4_intent") or {}).get("event_type"),
            "layer4_intent": plan_5_1_3.get("layer4_intent", {}),
            "layer4_output": plan_5_1_3.get("layer4_output", {}),
            "extra_context": (plan_5_1_3.get("layer4_output") or {}).get("candidate_generation", {}).get("extra_context", {}),
        }
    )
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    ranked_candidates = [candidate_experience_from_ranked(item) for item in plan_5_1_3.get("ranked_bundles", [])]
    selected_ranked = plan_5_1_3.get("selected_bundle") or {}
    selected = candidate_experience_from_ranked(selected_ranked) if selected_ranked else None
    approval = plan_5_1_3.get("final_safety_approval") or {}
    outcome = {
        "execution_status": execution_result.get("execution_status", "unknown"),
        "energy_saved_percent": execution_result.get("energy_saved_percent"),
        "carbon_reduced_percent": execution_result.get("carbon_reduced_percent"),
        "comfort_status": execution_result.get("comfort_status"),
        "anomaly_count": execution_result.get("anomaly_count"),
        "reward": learning_report.get("actual_reward"),
        "bandit_updated": bool(learning_report.get("bandit_updated", False)),
        "memory_updated": bool(learning_report.get("memory_updated", False)),
        "knowledge_graph_updated": bool(learning_report.get("knowledge_graph_updated", False)),
        "real_building_execution": False,
        "digital_twin_execution": execution_result.get("execution_status") == "executed",
    }
    experience_id = f"exp_{created.replace(':', '').replace('-', '').replace('+', 'z')}_{situation.get('event_type', 'event')}"
    episode = {
        "experience_id": experience_id,
        "created_at": created,
        "situation": situation,
        "candidate_plans": ranked_candidates,
        "selected_plan": selected,
        "approved_actions": approval.get("approved_actions", []),
        "blocked_actions": [item.get("action", item) for item in approval.get("blocked_actions", [])],
        "execution_outcome": outcome,
        "lessons_learned": lessons_from_execution(plan_5_1_3, execution_result, learning_report),
        "confidence": 0.92 if outcome["comfort_status"] == "Safe" and outcome["reward"] is not None and outcome["reward"] > 0 else 0.65,
        "tags": list(dict.fromkeys([situation.get("event_type"), situation.get("goal"), "digital_twin"])),
        "source": "layer5_closed_loop_execution",
    }
    result = append_experience_episode(episode)
    return {
        "experience_graph_updated": result["experience_graph_updated"],
        "experience_id": result["experience_id"],
        "similar_experiences_used": (plan_5_1_3.get("experience_prior_summary") or {}).get("similar_experiences_found", 0),
        "experience_confidence": episode["confidence"],
        "lessons_learned": episode["lessons_learned"],
        "real_building_execution": False,
        "digital_twin_execution": outcome["digital_twin_execution"],
    }

