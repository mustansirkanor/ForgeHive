def build_operator_explanation(operator_output: dict) -> str:
    user_message = operator_output.get("user_message", "")
    intent = operator_output.get("intent", {})
    building = operator_output.get("building_summary", {})
    knowledge = operator_output.get("knowledge_context", {})
    candidate_count = operator_output.get("candidate_count", 0)
    primary = operator_output.get("primary_candidate") or {}
    provider_trace = operator_output.get("llm_provider_trace", {})
    guardrails = operator_output.get("safety_guardrails", [])

    score = building.get("overall_score", building.get("overallScore", 0))
    comfort = building.get("comfort_status", building.get("comfortStatus", "unknown"))
    anomalies = building.get("anomaly_count", building.get("anomalyCount", 0))
    provider = provider_trace.get("selected_provider") or "none"
    kg_summary = knowledge.get("summary") or "No specific knowledge graph match was required."
    primary_name = primary.get("bundle_name") or "none selected yet"

    return (
        f"User asked: {user_message}. ForgeHive detected intent '{intent.get('intent')}' "
        f"with goal '{intent.get('goal')}' because {intent.get('routing_reason', 'the request matched Layer 4 routing rules')} "
        f"The current building snapshot shows score {score}, comfort status {comfort}, and {anomalies} anomalies. "
        f"Knowledge graph context: {kg_summary} "
        f"Layer 4 generated {candidate_count} candidate bundle(s); primary candidate for review is {primary_name}. "
        f"LLM/provider trace selected {provider}. "
        f"Safety guardrails remain active ({len(guardrails)} guardrail notes), and execution is disabled in Layer 4. "
        "ForgeHive did not run EnergyPlus or apply controls here because this layer is reasoning-only. "
        "Layer 5 will simulate candidate bundles, rank them with reward-style scoring, request Safety Governor approval, "
        "execute only approved digital-twin actions, and record feedback to memory, the knowledge graph, and the bandit selector."
    )
