from backend.app.cognitive.candidate_bundle_generator import generate_candidate_action_bundles
from backend.app.cognitive.knowledge_graph import record_operator_trace_to_kg
from backend.app.cognitive.llm_client import get_llm_mode
from backend.app.cognitive.mcp_tool_registry import (
    execute_mcp_tool,
    get_layer4_guardrail_summary,
    list_mcp_tools,
)


def normalize_operator_goal(user_input: str | None) -> dict:
    text = (user_input or "").lower()
    if any(word in text for word in ["empty", "vacant", "meeting ended", "room free"]):
        return {"goal": "reduce_energy_keep_comfort_safe", "event_type": "empty_room_detected", "reason": "Detected empty-room energy saving opportunity."}
    if any(word in text for word in ["co2", "air", "iaq", "stuffy"]):
        return {"goal": "fix_anomalies", "event_type": "iaq_risk_detected", "reason": "Detected IAQ or air quality concern."}
    if any(word in text for word in ["carbon", "emissions"]):
        return {"goal": "reduce_carbon", "event_type": "operator_request", "reason": "Detected carbon reduction goal."}
    if any(word in text for word in ["comfort", "hot", "cold"]):
        return {"goal": "maintain_comfort", "event_type": "operator_request", "reason": "Detected comfort goal."}
    if any(word in text for word in ["issue", "fault", "anomaly"]):
        return {"goal": "fix_anomalies", "event_type": "operator_request", "reason": "Detected issue or anomaly goal."}
    return {"goal": "balanced_optimization", "event_type": "operator_request", "reason": "Defaulted to balanced optimization."}


def create_operator_trace_step(step_name: str, tool_name: str | None, result_summary: str, success: bool) -> dict:
    return {"step_name": step_name, "tool_name": tool_name, "result_summary": result_summary, "success": success}


def summarize_tool_result(tool_name: str, result: dict) -> str:
    if not result.get("success"):
        return f"{tool_name} failed: {result.get('error')}"
    payload = result.get("result", {})
    if tool_name == "get_building_intelligence_package":
        return f"Loaded score {payload.get('score', {}).get('overall')} with comfort {payload.get('comfort', {}).get('status')}."
    if tool_name == "get_autonomous_decision":
        return f"Decision ready={payload.get('decision', {}).get('ready_for_execution')}."
    return f"{tool_name} succeeded."


def run_cognitive_operator(user_input: str, extra_context: dict | None = None, normalized_override: dict | None = None) -> dict:
    normalized = normalized_override or normalize_operator_goal(user_input)
    normalized.setdefault("reason", "Provided by upstream natural language intent classifier.")
    guardrails = get_layer4_guardrail_summary()
    tool_trace = []

    intelligence_result = execute_mcp_tool("get_building_intelligence_package")
    tool_trace.append(create_operator_trace_step("observe_building", "get_building_intelligence_package", summarize_tool_result("get_building_intelligence_package", intelligence_result), intelligence_result.get("success", False)))
    building = intelligence_result.get("result", {}) if intelligence_result.get("success") else {}

    candidate_result = generate_candidate_action_bundles(normalized["goal"], normalized["event_type"], extra_context)
    tool_trace.append(create_operator_trace_step("generate_candidate_bundles", "generate_candidate_action_bundles", f"Generated {len(candidate_result.get('candidate_bundles', []))} valid bundles.", True))

    decision_result = execute_mcp_tool("get_autonomous_decision", {"goal": normalized["goal"]})
    tool_trace.append(create_operator_trace_step("get_layer3_decision", "get_autonomous_decision", summarize_tool_result("get_autonomous_decision", decision_result), decision_result.get("success", False)))

    for bundle in candidate_result.get("candidate_bundles", []):
        validation_result = execute_mcp_tool("validate_action_bundle", {"bundle": bundle})
        tool_trace.append(create_operator_trace_step("validate_candidate_bundle", "validate_action_bundle", f"Bundle {bundle.get('bundle_name')} valid={validation_result.get('result', {}).get('valid')}.", validation_result.get("success", False)))

    ready_for_layer5 = bool(candidate_result.get("candidate_bundles")) and decision_result.get("success", False) and not guardrails["llm_can_execute_actions"]
    result = {
        "project": {"name": "ForgeHive", "layer": "Layer 4", "phase": "Phase 4.5", "description": "Cognitive MCP tool-calling operator with safe LLM provider fallback"},
        "user_input": user_input,
        "normalized": normalized,
        "guardrails": guardrails,
        "tool_trace": tool_trace,
        "building_snapshot": {
            "overall_score": building.get("score", {}).get("overall", 0),
            "comfort_status": building.get("comfort", {}).get("status", "Safe"),
            "anomaly_count": building.get("anomalies", {}).get("anomaly_count", 0),
        },
        "candidate_bundle_generation": candidate_result,
        "experience_graph": candidate_result.get("experience_graph", {}),
        "experience_retrieval": candidate_result.get("experience_retrieval", {}),
        "autonomous_decision": decision_result.get("result", {}),
        "execution_allowed": False,
        "ready_for_layer5": ready_for_layer5,
        "summary": "",
    }
    result["summary"] = explain_cognitive_result(result)
    record_operator_trace_to_kg({"user_input": user_input, "normalized": normalized, "tool_trace": tool_trace, "ready_for_layer5": ready_for_layer5})
    return result


def explain_cognitive_result(result: dict) -> str:
    bundles = result.get("candidate_bundle_generation", {}).get("candidate_bundles", [])
    decision = result.get("autonomous_decision", {}).get("decision", {})
    strategy = (decision.get("selected_action") or {}).get("strategy_name", "")
    return (
        f"User asked: {result.get('user_input')}. Detected goal {result['normalized']['goal']} "
        f"and event {result['normalized']['event_type']}. Called {len(result.get('tool_trace', []))} MCP-style steps, "
        f"generated {len(bundles)} candidate bundles, and Layer 3 suggested {strategy}. "
        "Execution did not happen because Layer 4 cannot execute actions. Layer 5 will simulate, rank, approve, and execute."
    )


def get_layer4_status() -> dict:
    return {
        "phase_4_2_candidate_generation": True,
        "phase_4_3_cognitive_operator": True,
        "phase_4_4_knowledge_graph_context": True,
        "phase_4_5_llm_provider_integration": True,
        "phase_4_6_natural_language_operator": True,
        "llm_mode": get_llm_mode(),
        "execution_enabled": False,
        "mcp_tools_available": len(list_mcp_tools()),
        "knowledge_graph_enabled": True,
        "summary": "Layer 4 can reason with MCP tools and generate candidate bundles, but cannot execute actions.",
    }
