import copy
import json

from backend.app.cognitive.action_bundle_schema import (
    create_demo_empty_room_bundle,
    to_dict,
)
from backend.app.cognitive.mcp_tool_registry import (
    execute_mcp_tool,
    get_layer4_guardrail_summary,
    get_mcp_tool_spec,
    is_tool_allowed_for_llm,
    list_mcp_tools,
)


if __name__ == "__main__":
    tools = list_mcp_tools()
    tool_names = [tool["tool_name"] for tool in tools]
    guardrails = get_layer4_guardrail_summary()
    print(json.dumps(guardrails, indent=2))

    intelligence_result = execute_mcp_tool("get_building_intelligence_package")
    decision_result = execute_mcp_tool(
        "get_autonomous_decision",
        {"goal": "reduce energy while keeping comfort safe"},
    )
    carbon_result = execute_mcp_tool("build_carbon_aware_plan")
    safety_result = execute_mcp_tool("check_action_safety", {"demo": "safe"})

    bundle = create_demo_empty_room_bundle()
    bundle_dict = to_dict(bundle)
    valid_bundle_result = execute_mcp_tool("validate_action_bundle", {"bundle": bundle_dict})

    invalid_bundle = copy.deepcopy(bundle_dict)
    invalid_bundle["actions"][2]["parameters"]["ventilation_percent"] = 0
    invalid_bundle_result = execute_mcp_tool("validate_action_bundle", {"bundle": invalid_bundle})

    future_execution_result = execute_mcp_tool("apply_approved_action_bundle", {"anything": True})

    print(json.dumps({"registered_tool_names": tool_names}, indent=2))
    print(json.dumps({"sample_autonomous_decision": decision_result}, indent=2))
    print(json.dumps({"valid_bundle_validation": valid_bundle_result}, indent=2))
    print(json.dumps({"invalid_bundle_validation": invalid_bundle_result}, indent=2))
    print(json.dumps({"future_execution_result": future_execution_result}, indent=2))

    passed = (
        len(tools) >= 12
        and bool(get_mcp_tool_spec("get_building_intelligence_package"))
        and bool(get_mcp_tool_spec("get_autonomous_decision"))
        and bool(get_mcp_tool_spec("validate_action_bundle"))
        and bool(get_mcp_tool_spec("apply_approved_action_bundle"))
        and is_tool_allowed_for_llm("apply_approved_action_bundle") is False
        and bool(get_mcp_tool_spec("simulate_action_bundle"))
        and is_tool_allowed_for_llm("simulate_action_bundle") is False
        and intelligence_result["success"] is True
        and intelligence_result["result"] is not None
        and decision_result["success"] is True
        and bool(decision_result["result"].get("decision"))
        and bool(decision_result["result"].get("project"))
        and carbon_result["success"] is True
        and carbon_result["result"]["strategy_name"] == "carbon_aware_mode"
        and safety_result["success"] is True
        and safety_result["result"]["approved"] is True
        and valid_bundle_result["success"] is True
        and valid_bundle_result["result"]["valid"] is True
        and invalid_bundle_result["success"] is True
        and invalid_bundle_result["result"]["valid"] is False
        and len(invalid_bundle_result["result"]["errors"]) > 0
        and future_execution_result["success"] is False
        and future_execution_result["allowed"] is False
    )

    if passed:
        print("\nPhase 4.1 test passed: MCP tool registry and action bundle guardrails are working.")
    else:
        print("\nPhase 4.1 test failed: MCP tool registry or guardrails did not meet expected checks.")
        raise SystemExit(1)
