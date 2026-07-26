def build_experience_context_for_llm(retrieved_experience: dict) -> str:
    if not retrieved_experience or not retrieved_experience.get("similar_experiences_found"):
        return (
            "No similar previous experience found. ForgeHive will explore safely using simulation and safety checks.\n"
            "Previous experiences are advisory when present. Current safety rules override history. "
            "Safety Governor remains final authority. Real building execution is not allowed."
        )

    lines = ["Previous similar operational experiences:"]
    for index, match in enumerate(retrieved_experience.get("top_matches", [])[:3], start=1):
        actions = ", ".join(match.get("recommended_actions", []) or ["none"])
        lines.extend(
            [
                "",
                f"{index}. Situation: {str(match.get('event_type', 'unknown')).replace('_', ' ')}.",
                f"   Best historical plan: {match.get('selected_plan_name')}.",
                f"   Actions that worked: {actions}.",
                f"   Result: {match.get('energy_saved_percent')}% energy saved, comfort {match.get('comfort_status')}, reward {match.get('reward')}.",
                f"   Confidence: {match.get('confidence')}.",
            ]
        )

    recommendation = retrieved_experience.get("historical_recommendation") or {}
    for pattern in recommendation.get("failure_patterns", [])[:3]:
        lines.extend(
            [
                "",
                f"Failed pattern: {pattern.get('action_type')} in {pattern.get('situation_type')} caused {pattern.get('failure_reason')}.",
                f"Avoid: {pattern.get('avoidance_rule')}",
            ]
        )

    lines.extend(
        [
            "",
            "Use these experiences to generate candidate action bundles.",
            "Do not blindly repeat history.",
            "Previous experiences are advisory.",
            "Current safety rules override history.",
            "Safety Governor remains final authority.",
            "Real building execution is not allowed.",
            "Still respect current comfort, IAQ, carbon, and Safety Governor constraints.",
        ]
    )
    return "\n".join(lines)

