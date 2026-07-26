from backend.app.cognitive.cognitive_operator import run_cognitive_operator
from backend.app.cognitive.explanation_engine import build_operator_explanation
from backend.app.cognitive.knowledge_graph import get_relevant_knowledge_context
from backend.app.cognitive.mcp_tool_registry import (
    execute_mcp_tool,
    get_layer4_guardrail_summary,
)
from backend.app.cognitive.operator_intents import classify_operator_intent


def build_building_summary(building_package: dict, dashboard_summary: dict | None = None) -> dict:
    dashboard_summary = dashboard_summary or {}
    return {
        "overall_score": building_package.get("score", {}).get("overall", dashboard_summary.get("overallScore", 0)),
        "grade": building_package.get("score", {}).get("grade", dashboard_summary.get("grade", "")),
        "comfort_status": building_package.get("comfort", {}).get("status", dashboard_summary.get("comfortStatus", "Safe")),
        "comfort_score": building_package.get("comfort", {}).get("comfort_score", dashboard_summary.get("comfortScore", 0)),
        "anomaly_count": building_package.get("anomalies", {}).get("anomaly_count", dashboard_summary.get("anomalyCount", 0)),
        "highest_anomaly_severity": building_package.get("anomalies", {}).get("highest_severity", dashboard_summary.get("highestAnomalySeverity", "none")),
        "summary": building_package.get("score", {}).get("summary", dashboard_summary.get("summary", "")),
    }


def build_layer5_handoff(candidate_count: int, intent: dict) -> dict:
    return {
        "ready": True,
        "goal": intent.get("goal"),
        "event_type": intent.get("event_type"),
        "candidate_count": candidate_count,
        "next_steps": [
            "Layer 5.1 will simulate candidate bundles in EnergyPlus.",
            "Layer 5.2 will rank plans using reward/RL-style scoring.",
            "Layer 5.3 will apply final Safety Governor approval.",
            "Layer 5.4 will execute only approved actions in the digital twin.",
            "Later Layer 5 feedback phases will record outcomes to memory, the knowledge graph, and the bandit selector.",
        ],
    }


def summarize_candidate(bundle: dict | None) -> dict | None:
    if not bundle:
        return None
    return {
        "bundle_name": bundle.get("bundle_name"),
        "goal": bundle.get("goal"),
        "event_type": bundle.get("event_type"),
        "action_count": len(bundle.get("actions", [])),
        "action_types": [action.get("action_type") for action in bundle.get("actions", [])],
        "requires_simulation": bundle.get("requires_simulation", True),
        "fallback_used": bundle.get("fallback_used", False),
        "rationale": bundle.get("rationale", ""),
    }


def empty_provider_trace() -> dict:
    return {
        "selected_provider": None,
        "attempted_providers": [],
        "fallback_used": False,
        "error_summary": None,
        "model": None,
        "latency_ms": 0,
        "schema_repair_applied": False,
        "repair_notes": [],
        "retry_count": 0,
        "timed_out": False,
    }


def run_natural_language_operator(user_message: str, extra_context: dict | None = None) -> dict:
    intent = classify_operator_intent(user_message)
    guardrail_summary = get_layer4_guardrail_summary()
    safety_guardrails = guardrail_summary.get("guardrails", [])

    intelligence_result = execute_mcp_tool("get_building_intelligence_package")
    building_package = intelligence_result.get("result", {}) if intelligence_result.get("success") else {}

    dashboard_result = execute_mcp_tool("get_dashboard_summary")
    dashboard_summary = dashboard_result.get("result", {}) if dashboard_result.get("success") else {}
    building_summary = build_building_summary(building_package, dashboard_summary)

    knowledge_context = get_relevant_knowledge_context(
        intent["goal"],
        intent["event_type"],
        building_package,
    )

    candidate_result = {}
    candidate_bundles = []
    cognitive_trace = {}
    llm_provider_trace = empty_provider_trace()

    should_generate_candidates = intent["action_oriented"] or intent["intent"] == "explain_decision"
    if should_generate_candidates:
        generation_goal = intent["goal"]
        generation_event = intent["event_type"]
        generation_context = {
            **(extra_context or {}),
            "operator_request": user_message,
            "request_analysis": intent.get("request_analysis", {}),
            "required_outcomes": intent.get("request_analysis", {}).get("requirements", []),
        }
        if intent["intent"] == "explain_decision":
            generation_goal = "reduce_energy_keep_comfort_safe"
            generation_event = "empty_room_detected"
            generation_context = {"demo_explanation_trace": True, **generation_context}

        cognitive_trace = run_cognitive_operator(
            user_message,
            generation_context,
            {
                "goal": generation_goal,
                "event_type": generation_event,
                "reason": intent.get("routing_reason", "Mapped by natural language operator intent classifier."),
            },
        )
        candidate_result = cognitive_trace.get("candidate_bundle_generation", {})
        candidate_bundles = candidate_result.get("candidate_bundles", [])
        llm_provider_trace = candidate_result.get("llm_result", empty_provider_trace())

    primary_candidate = summarize_candidate(candidate_bundles[0] if candidate_bundles else None)
    layer5_handoff = build_layer5_handoff(len(candidate_bundles), intent)

    output = {
        "project": {
            "name": "ForgeHive",
            "layer": "Layer 4",
            "phase": "Phase 4.6",
            "description": "Natural language building operator with explainable cognitive trace",
        },
        "user_message": user_message,
        "intent": intent,
        "building_summary": building_summary,
        "knowledge_context": knowledge_context,
        "candidate_bundles": candidate_bundles,
        "candidate_bundle_summary": [summarize_candidate(bundle) for bundle in candidate_bundles],
        "candidate_count": len(candidate_bundles),
        "primary_candidate": primary_candidate,
        "candidate_generation": candidate_result,
        "experience_graph": candidate_result.get("experience_graph", {}),
        "experience_retrieval": candidate_result.get("experience_retrieval", {}),
        "llm_experience_context": candidate_result.get("llm_experience_context", ""),
        "cognitive_trace": cognitive_trace,
        "llm_provider_trace": llm_provider_trace,
        "safety_guardrails": safety_guardrails,
        "guardrail_summary": guardrail_summary,
        "execution_enabled": False,
        "execution_allowed": False,
        "reasoning_only": True,
        "ready_for_layer5": True,
        "layer5_handoff": layer5_handoff,
        "dashboard": {
            "intent": intent["intent"],
            "goal": intent["goal"],
            "candidateCount": len(candidate_bundles),
            "selectedProvider": llm_provider_trace.get("selected_provider"),
            "executionEnabled": False,
            "reasoningOnly": True,
            "readyForLayer5": True,
        },
        "tool_trace": [
            {
                "step_name": "classify_intent",
                "tool_name": "classify_operator_intent",
                "success": True,
                "result_summary": intent["routing_reason"],
            },
            {
                "step_name": "observe_building",
                "tool_name": "get_building_intelligence_package",
                "success": intelligence_result.get("success", False),
                "result_summary": f"Loaded score {building_summary.get('overall_score')} and comfort {building_summary.get('comfort_status')}.",
            },
            {
                "step_name": "retrieve_knowledge_context",
                "tool_name": "get_relevant_knowledge_context",
                "success": True,
                "result_summary": knowledge_context.get("summary", ""),
            },
            {
                "step_name": "generate_candidate_bundles",
                "tool_name": "generate_candidate_action_bundles" if should_generate_candidates else None,
                "success": True,
                "result_summary": f"Generated {len(candidate_bundles)} candidate bundle(s).",
            },
        ],
        "explanation": "",
    }
    output["explanation"] = build_operator_explanation(output)
    return output
