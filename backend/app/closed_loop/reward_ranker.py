from backend.app.cognitive.knowledge_graph import get_relevant_knowledge_context
from backend.app.cognitive.provider_schema_normalizer import CANONICAL_ACTION_TYPES
from backend.app.decision.strategy_bandit import load_bandit_state
from backend.app.experience.experience_ranker import apply_experience_prior_to_candidate_bundles


def calculate_simulation_reward(simulation_result: dict) -> dict:
    energy_score = float(simulation_result.get("energy_saved_percent", 0) or 0)
    carbon_score = float(simulation_result.get("carbon_reduced_percent", 0) or 0) * 0.8

    comfort_status = simulation_result.get("comfort_status", "Unknown")
    if comfort_status == "Safe":
        comfort_score = 15
    elif comfort_status == "Warning":
        comfort_score = 5
    elif comfort_status == "Unsafe":
        comfort_score = -25
    else:
        comfort_score = 0
    comfort_score -= float(simulation_result.get("comfort_violation_minutes", 0) or 0) * 0.05

    anomaly_score = -int(simulation_result.get("anomaly_count", 0) or 0) * 3
    simulation_success_score = 5 if simulation_result.get("simulation_status") == "success" else -50
    safety_pre_score = 10
    for action in simulation_result.get("actions_simulated", []):
        if action.get("action_type") not in CANONICAL_ACTION_TYPES:
            safety_pre_score = 0
            break

    reward_score = energy_score + carbon_score + comfort_score + anomaly_score + simulation_success_score + safety_pre_score
    return {
        "reward_score": round(reward_score, 4),
        "energy_score": round(energy_score, 4),
        "carbon_score": round(carbon_score, 4),
        "comfort_score": round(comfort_score, 4),
        "anomaly_score": round(anomaly_score, 4),
        "simulation_success_score": simulation_success_score,
        "safety_pre_score": safety_pre_score,
    }


def calculate_final_penalty(simulation_result: dict) -> dict:
    penalty = 0.0
    reasons = []

    if simulation_result.get("simulation_status") != "success":
        penalty -= 1000.0
        reasons.append("simulation_status is not success")

    comfort_status = simulation_result.get("comfort_status")
    if comfort_status == "Unsafe":
        penalty -= 500.0
        reasons.append("comfort_status is Unsafe")
    elif comfort_status == "Warning":
        penalty -= 25.0
        reasons.append("comfort_status is Warning")

    return {
        "final_penalty": penalty,
        "penalty_reasons": reasons,
    }


def closest_strategy_for_bundle(bundle: dict) -> str:
    action_types = {action.get("action_type") for action in bundle.get("actions", [])}
    event_type = bundle.get("event_type", "")
    goal = bundle.get("goal", "")
    if "carbon_schedule_shift" in action_types:
        return "carbon_aware_mode"
    if "ventilation_adjustment" in action_types and "iaq" in event_type:
        return "iaq_priority_mode"
    if {"hvac_setpoint_adjustment", "lighting_adjustment", "ventilation_adjustment"}.intersection(action_types) and "empty_room" in event_type:
        return "eco_mode"
    if "comfort" in goal or any(action.get("parameters", {}).get("mode") == "comfort_mode" for action in bundle.get("actions", [])):
        return "comfort_mode"
    if "anomaly" in event_type:
        return "anomaly_response_mode"
    return "balanced_mode"


def get_bandit_prior_for_bundle(bundle: dict) -> float:
    strategy = closest_strategy_for_bundle(bundle)
    state = load_bandit_state()
    strategy_state = state.get("strategies", {}).get(strategy, {})
    return float(strategy_state.get("average_reward", 0.0) or 0.0)


def get_kg_relevance_score(bundle: dict, goal: str, event_type: str) -> dict:
    kg_context = get_relevant_knowledge_context(goal, event_type, {})
    relevant_actions = set(kg_context.get("relevant_actions", []))
    relevant_strategies = set(kg_context.get("relevant_strategies", []))
    matched_actions = []
    matched_strategies = []

    for action in bundle.get("actions", []):
        action_type = action.get("action_type")
        if action_type in relevant_actions:
            matched_actions.append(action_type)
        mode = action.get("parameters", {}).get("mode")
        if mode in relevant_strategies:
            matched_strategies.append(mode)

    strategy = closest_strategy_for_bundle(bundle)
    if strategy in relevant_strategies:
        matched_strategies.append(strategy)

    score = min(10, (len(set(matched_actions)) * 2) + (len(set(matched_strategies)) * 2))
    return {
        "score": score,
        "matched_actions": sorted(set(matched_actions)),
        "matched_strategies": sorted(set(matched_strategies)),
        "kg_summary": kg_context.get("summary", ""),
    }


def find_original_bundle(simulation_result: dict, original_bundles: list[dict]) -> dict:
    bundle_id = simulation_result.get("bundle_id")
    bundle_name = simulation_result.get("bundle_name")
    for bundle in original_bundles:
        if bundle.get("bundle_id") == bundle_id or bundle.get("bundle_name") == bundle_name:
            return bundle
    return {
        "bundle_id": bundle_id,
        "bundle_name": bundle_name,
        "goal": "",
        "event_type": "",
        "actions": [],
    }


def conservative_tiebreaker(bundle: dict) -> int:
    name = str(bundle.get("bundle_name", "")).lower()
    if "conservative" in name:
        return 0
    if "balanced" in name:
        return 1
    if "aggressive" in name:
        return 2
    return 1


def summarize_experience_prior(retrieved_experience: dict | None) -> dict:
    recommendation = (retrieved_experience or {}).get("historical_recommendation") or {}
    return {
        "similar_experiences_found": (retrieved_experience or {}).get("similar_experiences_found", 0),
        "preferred_historical_plan": recommendation.get("preferred_plan"),
        "actions_preferred": recommendation.get("actions_to_prefer", []),
        "actions_avoided": recommendation.get("actions_to_avoid", []),
        "average_reward": recommendation.get("average_reward"),
        "success_rate": recommendation.get("success_rate"),
        "reason": recommendation.get("reason") or (retrieved_experience or {}).get("message", ""),
    }


def rank_simulated_bundles(
    simulation_results: list[dict],
    original_bundles: list[dict],
    goal: str,
    event_type: str,
    retrieved_experience: dict | None = None,
) -> dict:
    experience_prior = apply_experience_prior_to_candidate_bundles(original_bundles, retrieved_experience or {})
    experience_by_id = {
        bundle.get("bundle_id"): bundle
        for bundle in experience_prior.get("candidate_bundles", [])
        if isinstance(bundle, dict)
    }
    experience_by_name = {
        bundle.get("bundle_name"): bundle
        for bundle in experience_prior.get("candidate_bundles", [])
        if isinstance(bundle, dict)
    }
    ranked = []
    for result in simulation_results or []:
        bundle = find_original_bundle(result, original_bundles)
        experience_bundle = experience_by_id.get(bundle.get("bundle_id")) or experience_by_name.get(bundle.get("bundle_name")) or {}
        reward = calculate_simulation_reward(result)
        bandit_prior = get_bandit_prior_for_bundle(bundle)
        kg = get_kg_relevance_score(bundle, goal, event_type)
        penalty = calculate_final_penalty(result)
        experience_prior_score = float(experience_bundle.get("experience_prior_score", 0.0) or 0.0)
        final_score = reward["reward_score"] + (0.25 * bandit_prior) + (0.5 * kg["score"]) + experience_prior_score + penalty["final_penalty"]
        penalty_text = (
            f" Penalties applied: {', '.join(penalty['penalty_reasons'])}."
            if penalty["penalty_reasons"]
            else " No final safety or simulation penalties applied."
        )

        ranked.append(
            {
                "rank": 0,
                "bundle_id": result.get("bundle_id"),
                "bundle_name": result.get("bundle_name"),
                "total_score": round(final_score, 4),
                "final_score": round(final_score, 4),
                "base_reward_score": reward["reward_score"],
                "reward_score": reward["reward_score"],
                "energy_score": reward["energy_score"],
                "carbon_score": reward["carbon_score"],
                "comfort_score": reward["comfort_score"],
                "safety_score": reward["safety_pre_score"],
                "anomaly_score": reward["anomaly_score"],
                "bandit_prior_score": bandit_prior,
                "kg_relevance_score": kg["score"],
                "knowledge_graph_score": kg["score"],
                "experience_prior_score": round(experience_prior_score, 4),
                "experience_prior_reasons": experience_bundle.get("experience_prior_reasons", []),
                "final_penalty": penalty["final_penalty"],
                "penalty_reasons": penalty["penalty_reasons"],
                "kg_details": kg,
                "simulation_result": result,
                "original_bundle": bundle,
                "ranking_reason": (
                    f"Reward={reward['reward_score']}, bandit_prior={bandit_prior}, "
                    f"kg_score={kg['score']}, experience_prior={experience_prior_score}, "
                    f"final_penalty={penalty['final_penalty']}."
                    f"{penalty_text}"
                ),
            }
        )

    ranked.sort(
        key=lambda item: (
            item["simulation_result"].get("simulation_status") != "success",
            item["simulation_result"].get("comfort_status") == "Unsafe",
            -item["total_score"],
            float(item["simulation_result"].get("comfort_violation_minutes", 0) or 0),
            -float(item["simulation_result"].get("energy_saved_percent", 0) or 0),
            conservative_tiebreaker(item.get("original_bundle", {})),
        )
    )

    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    selected = ranked[0] if ranked and ranked[0]["simulation_result"].get("simulation_status") == "success" else None
    return {
        "ranked_bundles": ranked,
        "selected_bundle": selected,
        "ranking_summary": f"Ranked {len(ranked)} bundle(s); selected {selected.get('bundle_name') if selected else 'safe no-action'}." if ranked else "No bundles available to rank.",
        "rl_used": True,
        "kg_used": True,
        "experience_prior_used": bool(experience_prior.get("experience_prior_used", False)),
        "experience_prior_summary": summarize_experience_prior(retrieved_experience),
        "experience_bonus_summary": experience_prior.get("experience_bonus_summary", []),
        "experience_prior_warnings": experience_prior.get("warnings", []),
    }
