from backend.app.decision.action_schema import to_dict
from backend.app.decision.carbon_scheduler import (
    build_carbon_aware_plan,
    create_carbon_schedule_action,
)
from backend.app.decision.safety_governor import check_action_safety
from backend.app.decision.supervisor import run_multi_agent_supervisor


EXECUTION_NOTE = (
    "Layer 5.1-5.3 will simulate, rank, and safety-approve this plan; "
    "actual digital-twin execution is deferred to Phase 5.4."
)


def normalize_goal(user_goal: str | None) -> str:
    if not user_goal or not user_goal.strip():
        return "balanced_optimization"

    normalized = user_goal.lower()

    if any(word in normalized for word in ["anomaly", "issue", "fault", "fix"]):
        return "fix_anomalies"
    if "energy" in normalized:
        return "reduce_energy_keep_comfort_safe"
    if "carbon" in normalized:
        return "reduce_carbon"
    if "comfort" in normalized:
        return "maintain_comfort"

    return "balanced_optimization"


def build_action_plan(
    goal: str = "balanced_optimization",
    intelligence: dict | None = None,
) -> dict:
    normalized_goal = normalize_goal(goal)
    supervisor_decision = run_multi_agent_supervisor(
        goal=normalized_goal,
        intelligence=intelligence,
    )
    carbon_plan = None
    carbon_safety_decision = None
    carbon_action_dict = None

    if normalized_goal == "reduce_carbon":
        carbon_plan = build_carbon_aware_plan(intelligence)
        carbon_action = create_carbon_schedule_action(carbon_plan)
        carbon_safety_decision_obj = check_action_safety(carbon_action, intelligence)
        carbon_safety_decision = to_dict(carbon_safety_decision_obj)
        carbon_action_dict = to_dict(carbon_action)

    if normalized_goal == "reduce_carbon" and carbon_safety_decision and carbon_safety_decision["approved"]:
        selected_plan_type = "carbon_aware_schedule"
        selected_action = carbon_action_dict
        safety_decision = carbon_safety_decision
    else:
        selected_plan_type = "supervisor"
        selected_action = supervisor_decision.get("final_action")
        safety_decision = supervisor_decision.get("safety_decision", {})

    ready_for_execution = bool(safety_decision.get("approved", False))

    plan = {
        "goal": goal,
        "normalized_goal": normalized_goal,
        "supervisor_decision": supervisor_decision,
        "carbon_plan": carbon_plan,
        "selected_plan_type": selected_plan_type,
        "selected_action": selected_action,
        "safety_decision": safety_decision,
        "ready_for_execution": ready_for_execution,
        "execution_note": EXECUTION_NOTE,
        "summary": "",
    }
    plan["summary"] = explain_action_plan(plan)
    return plan


def explain_action_plan(plan: dict) -> str:
    selected_action = plan.get("selected_action") or {}
    safety_decision = plan.get("safety_decision") or {}
    strategy = selected_action.get("strategy_name", "no approved strategy")
    action_type = selected_action.get("action_type", "no action")
    approved = safety_decision.get("approved", False)
    status = "ready for Layer 5 closed-loop review" if approved else "not ready for execution"

    return (
        f"Goal '{plan.get('normalized_goal')}' selected {strategy} "
        f"via {plan.get('selected_plan_type')} with action type {action_type}; "
        f"the plan is {status}. {EXECUTION_NOTE}"
    )
