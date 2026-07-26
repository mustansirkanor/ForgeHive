from backend.app.decision.action_schema import to_dict
from backend.app.decision.domain_agents import (
    AgentRecommendation,
    get_all_agent_recommendations,
    recommendation_to_dict,
)
from backend.app.decision.safety_governor import check_action_safety
from backend.app.decision.strategy_bandit import (
    calculate_reward,
    choose_strategy_for_context,
    update_strategy_reward,
)
from backend.app.intelligence.intelligence_api import get_building_intelligence_package


PRIORITY_WEIGHT = {
    "low": 0,
    "medium": 5,
    "high": 10,
    "critical": 20,
}


def score_recommendation(
    recommendation: AgentRecommendation,
    goal: str,
    intelligence: dict,
    bandit_choice: dict | None = None,
) -> float:
    action = recommendation.recommended_action
    score = recommendation.confidence * 50

    if "reduce_energy" in goal:
        score += action.expected_energy_saved_percent
    if "reduce_carbon" in goal:
        score += action.expected_carbon_reduced_percent

    comfort_status = intelligence.get("comfort", {}).get("status", "Safe")
    if recommendation.agent_name == "comfort_agent" and comfort_status in ["Warning", "Unsafe"]:
        score += 15

    anomaly_count = intelligence.get("anomalies", {}).get("anomaly_count", 0)
    if recommendation.agent_name == "anomaly_agent" and anomaly_count > 0:
        score += 15

    if action.expected_comfort_impact == "positive":
        score += 10
    elif action.expected_comfort_impact == "negative":
        score -= 10

    score += PRIORITY_WEIGHT.get(action.priority, 0)

    if bandit_choice and action.strategy_name == bandit_choice.get("selected_strategy"):
        score += 15

    return round(score, 2)


def select_best_recommendation(
    recommendations: list[AgentRecommendation],
    goal: str,
    intelligence: dict,
    bandit_choice: dict | None = None,
) -> dict:
    scored = [
        {
            "selected": recommendation,
            "score": score_recommendation(recommendation, goal, intelligence, bandit_choice),
        }
        for recommendation in recommendations
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)

    ranked = [
        {
            "rank": index + 1,
            "agent_name": item["selected"].agent_name,
            "score": item["score"],
            "rationale": item["selected"].rationale,
            "action": to_dict(item["selected"].recommended_action),
        }
        for index, item in enumerate(scored)
    ]

    return {
        "selected": scored[0]["selected"],
        "ranked": ranked,
    }


def build_supervisor_summary(
    goal: str,
    agents_consulted: list[str],
    selected_recommendation: AgentRecommendation,
    safety_decision,
    bandit_choice: dict,
) -> str:
    action = selected_recommendation.recommended_action
    result = "approved" if safety_decision.approved else "rejected"
    bandit_strategy = bandit_choice.get("selected_strategy", "not_used")
    reason_text = "; ".join(safety_decision.reasons) if safety_decision.reasons else "No safety blockers found."
    return (
        f"Goal '{goal}' consulted {len(agents_consulted)} agents. "
        f"Selected {action.strategy_name} from {selected_recommendation.agent_name}; "
        f"bandit preferred {bandit_strategy}. Safety Governor {result} the action. "
        f"Reason summary: {reason_text}"
    )


def run_multi_agent_supervisor(
    goal: str = "balanced_optimization",
    intelligence: dict | None = None,
    use_bandit: bool = True,
) -> dict:
    current_intelligence = intelligence if intelligence is not None else get_building_intelligence_package()
    recommendations = get_all_agent_recommendations(current_intelligence, goal)
    bandit_choice = (
        choose_strategy_for_context(current_intelligence, goal)
        if use_bandit
        else {
            "selected_strategy": "",
            "selection_reason": "Bandit disabled for this supervisor run.",
            "context": {},
            "strategy_scores": {},
            "source": "disabled",
        }
    )
    selection = select_best_recommendation(recommendations, goal, current_intelligence, bandit_choice)
    selected_recommendation = selection["selected"]
    selected_action = selected_recommendation.recommended_action
    safety_decision = check_action_safety(selected_action, current_intelligence)
    safety_decision_dict = to_dict(safety_decision)

    if safety_decision.approved:
        final_action = to_dict(selected_action)
        status = "approved"
    else:
        final_action = safety_decision.safe_alternative
        status = "rejected"

    agents_consulted = [recommendation.agent_name for recommendation in recommendations]
    selected_score = selection["ranked"][0]["score"]

    return {
        "goal": goal,
        "agents_consulted": agents_consulted,
        "bandit_choice": bandit_choice,
        "recommendations": [
            recommendation_to_dict(recommendation)
            for recommendation in recommendations
        ],
        "ranked_recommendations": selection["ranked"],
        "selected_recommendation": recommendation_to_dict(selected_recommendation),
        "safety_decision": safety_decision_dict,
        "final_action": final_action,
        "status": status,
        "summary": build_supervisor_summary(
            goal,
            agents_consulted,
            selected_recommendation,
            safety_decision,
            bandit_choice,
        ),
    }


def get_decision_for_goal(goal: str) -> dict:
    return run_multi_agent_supervisor(goal)


def record_supervisor_feedback(decision_result: dict, actual_result: dict | None = None) -> dict:
    selected_action = decision_result.get("selected_recommendation", {}).get("recommended_action", {})
    safety_decision = decision_result.get("safety_decision", {})
    impact_source = actual_result or {}

    energy_saved_percent = float(
        impact_source.get("energy_saved_percent", selected_action.get("expected_energy_saved_percent", 0.0))
    )
    carbon_reduced_percent = float(
        impact_source.get("carbon_reduced_percent", selected_action.get("expected_carbon_reduced_percent", 0.0))
    )
    comfort_status = impact_source.get("comfort_status", "Safe" if safety_decision.get("approved") else "Warning")
    anomaly_count = int(impact_source.get("anomaly_count", 0))
    action_approved = bool(safety_decision.get("approved", False))

    reward = calculate_reward(
        energy_saved_percent=energy_saved_percent,
        carbon_reduced_percent=carbon_reduced_percent,
        comfort_status=comfort_status,
        anomaly_count=anomaly_count,
        action_approved=action_approved,
    )
    strategy_name = selected_action.get("strategy_name", "balanced_mode")
    bandit_state = update_strategy_reward(
        strategy_name,
        reward,
        metadata={
            "goal": decision_result.get("goal", ""),
            "status": decision_result.get("status", ""),
            "actual_result_provided": actual_result is not None,
        },
    )

    return {
        "reward_recorded": True,
        "strategy_name": strategy_name,
        "reward": reward,
        "bandit_state": bandit_state,
    }
