import json

from backend.app.cognitive.candidate_bundle_generator import generate_candidate_action_bundles
from backend.app.cognitive.cognitive_operator import (
    explain_cognitive_result,
    get_layer4_status,
    run_cognitive_operator,
)
from backend.app.cognitive.knowledge_graph import (
    ensure_knowledge_graph,
    get_relevant_knowledge_context,
)
from backend.app.cognitive.mcp_tool_registry import execute_mcp_tool


if __name__ == "__main__":
    ensure_knowledge_graph()

    kg_context = get_relevant_knowledge_context(
        goal="reduce_energy_keep_comfort_safe",
        event_type="empty_room_detected",
        building_context={
            "building_state": {
                "occupancy": {"total_occupancy": 0}
            },
            "comfort": {"status": "Safe"},
            "anomalies": {"anomaly_count": 0, "anomalies": []},
        },
    )

    candidate_generation = generate_candidate_action_bundles(
        goal="reduce_energy_keep_comfort_safe",
        event_type="empty_room_detected",
        extra_context={
            "next_meeting_minutes": 90,
            "room": "meeting_room",
        },
    )

    cognitive_result = run_cognitive_operator(
        "The meeting room is empty now. Save energy but keep it safe.",
        extra_context={
            "next_meeting_minutes": 90,
            "room": "meeting_room",
        },
    )

    mcp_candidate_result = execute_mcp_tool(
        "generate_candidate_action_bundles",
        {
            "goal": "reduce_energy_keep_comfort_safe",
            "event_type": "empty_room_detected",
            "extra_context": {"next_meeting_minutes": 45},
        },
    )

    blocked_execution_result = execute_mcp_tool("apply_approved_action_bundle", {"demo": True})

    layer4_status = get_layer4_status()
    explanation = explain_cognitive_result(cognitive_result)

    print(json.dumps(layer4_status, indent=2))
    print(json.dumps(kg_context, indent=2))
    print(json.dumps({
        "candidate_count": len(candidate_generation.get("candidate_bundles", [])),
        "context_summary": candidate_generation.get("context_summary"),
        "guardrails": candidate_generation.get("guardrails"),
    }, indent=2))
    print(json.dumps({"cognitive_operator_explanation": explanation}, indent=2))
    print(json.dumps({
        "mcp_candidate_success": mcp_candidate_result.get("success"),
        "candidate_count": len((mcp_candidate_result.get("result") or {}).get("candidate_bundles", [])),
    }, indent=2))
    print(json.dumps(blocked_execution_result, indent=2))

    candidate_bundles = candidate_generation.get("candidate_bundles", [])
    mcp_candidate_bundles = (mcp_candidate_result.get("result") or {}).get("candidate_bundles", [])

    passed = (
        bool(kg_context.get("matched_conditions"))
        and (
            "lighting_adjustment" in kg_context.get("relevant_actions", [])
            or "hvac_setpoint_adjustment" in kg_context.get("relevant_actions", [])
        )
        and bool(kg_context.get("summary"))
        and len(candidate_bundles) >= 2
        and all(bundle.get("actions") for bundle in candidate_bundles)
        and any(len(bundle.get("actions", [])) > 1 for bundle in candidate_bundles)
        and bool(candidate_generation.get("guardrails"))
        and cognitive_result["project"]["layer"] == "Layer 4"
        and cognitive_result["normalized"]["goal"] == "reduce_energy_keep_comfort_safe"
        and cognitive_result["normalized"]["event_type"] == "empty_room_detected"
        and bool(cognitive_result.get("tool_trace"))
        and bool(cognitive_result.get("candidate_bundle_generation"))
        and cognitive_result["execution_allowed"] is False
        and cognitive_result["ready_for_layer5"] is True
        and mcp_candidate_result["success"] is True
        and mcp_candidate_result["allowed"] is True
        and len(mcp_candidate_bundles) >= 2
        and blocked_execution_result["success"] is False
        and blocked_execution_result["allowed"] is False
    )

    if passed:
        print("\nPhase 4.2, 4.3 and 4.4 test passed: LLM candidate generation, cognitive MCP operator, and Knowledge Graph context are working.")
    else:
        print("\nPhase 4.2, 4.3 and 4.4 test failed: Cognitive layer did not meet expected checks.")
        raise SystemExit(1)
