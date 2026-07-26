from backend.app.experience.experience_store import load_experience_graph


def bundle_action_types(bundle: dict) -> set[str]:
    values = set()
    for action in bundle.get("actions", []) or []:
        action_type = action.get("action_type") or action.get("actionType")
        if action_type:
            values.add(action_type)
    values.update(bundle.get("action_types") or [])
    return values


def bundle_risks_comfort(bundle: dict) -> bool:
    name = str(bundle.get("bundle_name") or bundle.get("name") or "").lower()
    if "aggressive" in name or "shutdown" in name:
        return True
    for action in bundle.get("actions", []) or []:
        action_type = action.get("action_type") or action.get("actionType")
        params = action.get("parameters", {}) or {}
        if action_type == "hvac_shutdown":
            return True
        if action_type == "hvac_setpoint_adjustment" and float(params.get("cooling_setpoint_c") or 24) >= 29:
            return True
    return False


def apply_experience_prior_to_candidate_bundles(
    candidate_bundles: list[dict],
    retrieved_experience: dict,
) -> dict:
    recommendation = (retrieved_experience or {}).get("historical_recommendation")
    if not candidate_bundles or not recommendation:
        return {
            "candidate_bundles": candidate_bundles or [],
            "experience_prior_used": False,
            "experience_bonus_summary": [],
            "warnings": [],
        }

    preferred_actions = set(recommendation.get("actions_to_prefer") or [])
    preferred_plan = recommendation.get("preferred_plan")
    failure_patterns = recommendation.get("failure_patterns") or load_experience_graph().get("failure_patterns", [])
    failed_actions = {pattern.get("action_type") for pattern in failure_patterns if pattern.get("action_type")}
    comfort_failure = any(pattern.get("failure_reason") == "comfort_violation" for pattern in failure_patterns)
    warnings = []
    bonus_summary = []
    adjusted = []

    for bundle in candidate_bundles:
        copy = dict(bundle)
        action_types = bundle_action_types(copy)
        score = 0.0
        reasons = []
        if preferred_actions and action_types:
            overlap = len(action_types & preferred_actions) / max(len(action_types), 1)
            if overlap >= 0.5:
                score += 5
                reasons.append("matched >=50% of historically successful actions")
        if preferred_plan and (copy.get("bundle_name") or copy.get("name")) == preferred_plan:
            score += 5
            reasons.append("matched the preferred historical plan")
        if float(recommendation.get("success_rate") or 0) > 0.85:
            score += 3
            reasons.append("similar history has high comfort-safe success")
        matched_failures = sorted(action_types & failed_actions)
        if matched_failures:
            score -= 20
            reasons.append("matched known failed action(s): " + ", ".join(matched_failures))
        if comfort_failure and bundle_risks_comfort(copy):
            score -= 50
            reasons.append("historical comfort violation and this bundle risks comfort")
            warnings.append(f"Experience prior penalized {copy.get('bundle_name') or copy.get('name')} for comfort-risk history.")
        copy["experience_prior_score"] = round(score, 4)
        copy["experience_prior_reasons"] = reasons
        adjusted.append(copy)
        bonus_summary.append(
            {
                "bundle_name": copy.get("bundle_name") or copy.get("name"),
                "experience_prior_score": round(score, 4),
                "reasons": reasons,
            }
        )

    return {
        "candidate_bundles": adjusted,
        "experience_prior_used": True,
        "experience_bonus_summary": bonus_summary,
        "warnings": warnings,
    }

