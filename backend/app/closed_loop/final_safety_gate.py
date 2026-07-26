from backend.app.decision.action_schema import ControlAction, to_dict
from backend.app.decision.safety_governor import check_action_safety
from backend.app.cognitive.request_semantics import action_semantic_violations


EXECUTION_NOTE = (
    "Phase 5.3 approves an execution-ready plan only. Phase 5.4 will apply approved actions inside the EnergyPlus digital twin."
)


RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def target_includes_occupied(target: str) -> bool:
    normalized = str(target or "").lower()
    return "occupied" in normalized and "unoccupied" not in normalized


def expected_outcome_value(bundle: dict, key: str) -> float:
    try:
        return float(bundle.get("expected_outcome", {}).get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def action_to_control_action(action: dict, bundle: dict, strategy_name: str) -> ControlAction:
    parameters = dict(action.get("parameters") if isinstance(action.get("parameters"), dict) else {})
    if action.get("action_type") == "hvac_setpoint_adjustment":
        parameters.setdefault("applies_to_occupied_zones", target_includes_occupied(action.get("target", "")))
    if action.get("action_type") == "ventilation_adjustment":
        parameters.setdefault("applies_to_occupied_zones", target_includes_occupied(action.get("target", "")))

    return ControlAction(
        action_id=action.get("action_id", f"{bundle.get('bundle_id', bundle.get('bundle_name', 'bundle'))}_{action.get('action_type', 'action')}"),
        strategy_name=strategy_name,
        action_type=action.get("action_type", "no_direct_control_change"),
        target=action.get("target", "building"),
        description=action.get("description", "Layer 5 candidate action."),
        parameters=parameters,
        expected_energy_saved_percent=expected_outcome_value(bundle, "energy_saved_percent"),
        expected_carbon_reduced_percent=expected_outcome_value(bundle, "carbon_reduced_percent"),
        expected_comfort_impact=bundle.get("expected_outcome", {}).get("comfort_impact", "neutral"),
        source_agent="layer5_final_safety_gate",
        priority="medium",
    )


def safe_no_action_approval(selected_bundle_id=None, selected_bundle_name=None, safety_decisions=None, blocked_actions=None) -> dict:
    return {
        "approved": False,
        "selected_bundle_id": selected_bundle_id,
        "selected_bundle_name": selected_bundle_name,
        "risk_level": "low",
        "safety_decisions": safety_decisions or [],
        "blocked_actions": blocked_actions or [],
        "approved_actions": [],
        "safety_summary": "No actions are approved; safe no-action plan selected.",
        "execution_ready": False,
        "execution_applied": False,
        "execution_note": EXECUTION_NOTE,
    }


def run_final_safety_gate(selected_ranked_bundle: dict, original_bundle: dict, building_context: dict | None = None) -> dict:
    if not selected_ranked_bundle or not original_bundle:
        return safe_no_action_approval()

    strategy_name = selected_ranked_bundle.get("simulation_result", {}).get("strategy_name", "balanced_mode")
    safety_decisions = []
    blocked_actions = []
    approved_actions = []
    highest_risk = "low"
    critical_rejection = False

    for action in original_bundle.get("actions", []):
        control_action = action_to_control_action(action, original_bundle, strategy_name)
        control_action_dict = to_dict(control_action)
        request_analysis = (building_context or {}).get("request_analysis", {})
        semantic_reasons = action_semantic_violations(control_action_dict, request_analysis)
        if semantic_reasons:
            decision_dict = {
                "action_id": control_action.action_id,
                "approved": False,
                "decision": "rejected",
                "risk_level": "high",
                "reasons": semantic_reasons,
                "blocked_by": ["operator_request_semantics"],
                "safe_alternative": None,
                "checked_constraints": ["operator_request_semantics"],
                "action": control_action_dict,
            }
            safety_decisions.append(decision_dict)
            blocked_actions.append({"action": control_action_dict, "decision": decision_dict})
            highest_risk = "high"
            critical_rejection = True
            continue

        safety_intelligence = (building_context or {}).get("building_intelligence")
        decision = check_action_safety(control_action, safety_intelligence)
        decision_dict = to_dict(decision)
        decision_dict["action"] = to_dict(control_action)
        safety_decisions.append(decision_dict)
        if RISK_ORDER.get(decision.risk_level, 0) > RISK_ORDER.get(highest_risk, 0):
            highest_risk = decision.risk_level

        if decision.approved:
            approved_actions.append(to_dict(control_action))
        else:
            blocked_actions.append({"action": to_dict(control_action), "decision": decision_dict})
            if decision.risk_level in {"high", "critical"}:
                critical_rejection = True

    if not approved_actions:
        approval = safe_no_action_approval(
            selected_bundle_id=original_bundle.get("bundle_id", original_bundle.get("bundle_name")),
            selected_bundle_name=original_bundle.get("bundle_name"),
            safety_decisions=safety_decisions,
            blocked_actions=blocked_actions,
        )
        approval["risk_level"] = highest_risk
        return approval

    approved = not critical_rejection
    return {
        "approved": approved,
        "selected_bundle_id": original_bundle.get("bundle_id", original_bundle.get("bundle_name")),
        "selected_bundle_name": original_bundle.get("bundle_name"),
        "risk_level": highest_risk,
        "safety_decisions": safety_decisions,
        "blocked_actions": blocked_actions,
        "approved_actions": approved_actions if approved else [],
        "safety_summary": (
            f"Approved {len(approved_actions)} action(s); blocked {len(blocked_actions)} action(s)."
            if approved
            else "Critical/high-risk rejection blocked final approval."
        ),
        "execution_ready": approved and bool(approved_actions),
        "execution_applied": False,
        "execution_note": EXECUTION_NOTE,
    }
