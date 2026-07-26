from collections import Counter

from backend.app.experience.experience_store import load_experience_graph
from backend.app.experience.similarity import calculate_situation_similarity


def action_types(plan: dict) -> list[str]:
    values = list(plan.get("action_types") or [])
    for action in plan.get("actions", []) or []:
        action_type = action.get("action_type") or action.get("actionType")
        if action_type:
            values.append(action_type)
    return list(dict.fromkeys(values))


def selected_plan(episode: dict) -> dict:
    selected = episode.get("selected_plan") or {}
    selected_name = selected.get("bundle_name") or selected.get("name")
    for plan in episode.get("candidate_plans", []) or []:
        if plan.get("bundle_name") == selected_name or plan.get("bundle_id") == selected.get("bundle_id"):
            return {**plan, **selected}
    return selected


def summarize_match(episode: dict, similarity: float) -> dict:
    selected = selected_plan(episode)
    outcome = episode.get("execution_outcome") or {}
    return {
        "experience_id": episode.get("experience_id"),
        "similarity": similarity,
        "event_type": (episode.get("situation") or {}).get("event_type"),
        "selected_plan_name": selected.get("bundle_name") or selected.get("name"),
        "reward": outcome.get("reward", selected.get("reward")),
        "energy_saved_percent": outcome.get("energy_saved_percent", selected.get("simulated_energy_saved_percent")),
        "carbon_reduced_percent": outcome.get("carbon_reduced_percent", selected.get("simulated_carbon_reduced_percent")),
        "comfort_status": outcome.get("comfort_status", selected.get("simulated_comfort_status")),
        "confidence": episode.get("confidence", 0.5),
        "recommended_actions": action_types(selected),
        "lessons_learned": episode.get("lessons_learned", []),
    }


def build_historical_recommendation(matches: list[dict], graph: dict) -> dict | None:
    if not matches:
        return None
    plan_counts = Counter(match.get("selected_plan_name") for match in matches if match.get("selected_plan_name"))
    preferred_plan = plan_counts.most_common(1)[0][0] if plan_counts else None
    rewards = [float(match.get("reward") or 0) for match in matches]
    confidences = [float(match.get("confidence") or 0) for match in matches]
    action_counter = Counter()
    for match in matches:
        action_counter.update(match.get("recommended_actions", []))
    failure_patterns = graph.get("failure_patterns", [])
    actions_to_avoid = list(dict.fromkeys(pattern.get("action_type") for pattern in failure_patterns if pattern.get("action_type")))
    stats = graph.get("strategy_stats", {}).get(preferred_plan, {})
    success_rate = stats.get("success_rate")
    if success_rate is None:
        uses = max(int(stats.get("uses", 0) or len(matches)), 1)
        success_rate = float(stats.get("successes", len(matches)) or 0) / uses
    return {
        "preferred_plan": preferred_plan,
        "success_rate": round(float(success_rate or 0), 4),
        "average_reward": round(sum(rewards) / max(len(rewards), 1), 4),
        "confidence": round(sum(confidences) / max(len(confidences), 1), 4),
        "actions_to_prefer": [action for action, _ in action_counter.most_common(8)],
        "actions_to_avoid": actions_to_avoid[:8],
        "failure_patterns": failure_patterns[:5],
        "reason": f"Similar {matches[0].get('event_type')} experiences preserved comfort and saved energy.",
    }


def retrieve_similar_experiences(
    current_situation: dict,
    limit: int = 5,
    min_similarity: float = 0.35,
) -> dict:
    graph = load_experience_graph()
    scored = []
    for episode in graph.get("episodes", []):
        similarity = calculate_situation_similarity(current_situation, episode.get("situation") or {})
        if similarity >= min_similarity:
            scored.append((similarity, episode))
    scored.sort(key=lambda item: (item[0], item[1].get("confidence", 0)), reverse=True)
    top_matches = [summarize_match(episode, similarity) for similarity, episode in scored[:limit]]
    if not top_matches:
        return {
            "query_situation": current_situation,
            "similar_experiences_found": 0,
            "top_matches": [],
            "historical_recommendation": None,
            "message": "No similar previous experience found. ForgeHive will explore safely.",
        }
    return {
        "query_situation": current_situation,
        "similar_experiences_found": len(top_matches),
        "top_matches": top_matches,
        "historical_recommendation": build_historical_recommendation(top_matches, graph),
    }

