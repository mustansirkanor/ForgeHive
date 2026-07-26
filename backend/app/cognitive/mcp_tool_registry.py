from dataclasses import asdict, dataclass, is_dataclass

from backend.app.cognitive import mcp_tool_wrappers


@dataclass
class MCPToolSpec:
    tool_name: str
    description: str
    category: str
    layer: str
    backend_function: str
    input_schema: dict
    output_schema: dict
    read_only: bool
    implemented: bool
    requires_safety_check: bool
    can_execute_action: bool
    allowed_for_llm: bool
    guardrails: list[str]
    notes: list[str]


@dataclass
class MCPToolCallResult:
    tool_name: str
    success: bool
    result: dict | None
    error: str | None
    allowed: bool


def to_dict(obj) -> dict:
    if not is_dataclass(obj):
        raise TypeError("to_dict expects a dataclass object.")
    return asdict(obj)


def tool_spec(
    tool_name: str,
    description: str,
    category: str,
    layer: str,
    backend_function: str,
    read_only: bool = True,
    implemented: bool = True,
    requires_safety_check: bool = False,
    can_execute_action: bool = False,
    allowed_for_llm: bool = True,
    notes: list[str] | None = None,
) -> MCPToolSpec:
    return MCPToolSpec(
        tool_name=tool_name,
        description=description,
        category=category,
        layer=layer,
        backend_function=backend_function,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        read_only=read_only,
        implemented=implemented,
        requires_safety_check=requires_safety_check,
        can_execute_action=can_execute_action,
        allowed_for_llm=allowed_for_llm,
        guardrails=[
            "No direct action execution in Layer 4.1.",
            "Unsafe or invalid calls return errors.",
            "Safety Governor remains the final approval gate.",
        ],
        notes=notes or [],
    )


def get_registered_mcp_tools() -> dict[str, MCPToolSpec]:
    return {
        "get_building_intelligence_package": tool_spec(
            "get_building_intelligence_package",
            "Return the full Layer 2 building intelligence package.",
            "intelligence",
            "Layer 2",
            "backend.app.intelligence.intelligence_api.get_building_intelligence_package",
        ),
        "get_dashboard_summary": tool_spec(
            "get_dashboard_summary",
            "Return compact dashboard-ready building intelligence.",
            "intelligence",
            "Layer 2",
            "backend.app.intelligence.intelligence_api.get_dashboard_ready_intelligence",
        ),
        "get_autonomous_decision": tool_spec(
            "get_autonomous_decision",
            "Select and safety-check the best autonomous decision for a goal.",
            "decision",
            "Layer 3",
            "backend.app.decision.decision_api.get_autonomous_decision",
            requires_safety_check=True,
        ),
        "get_dashboard_ready_decision": tool_spec(
            "get_dashboard_ready_decision",
            "Return compact decision output for dashboard or explanation.",
            "decision",
            "Layer 3",
            "backend.app.decision.decision_api.get_dashboard_ready_decision",
        ),
        "run_multi_agent_supervisor": tool_spec(
            "run_multi_agent_supervisor",
            "Consult energy, comfort, carbon, and anomaly agents.",
            "decision",
            "Layer 3",
            "backend.app.decision.supervisor.run_multi_agent_supervisor",
            requires_safety_check=True,
        ),
        "check_action_safety": tool_spec(
            "check_action_safety",
            "Approve or reject a proposed action before execution.",
            "safety",
            "Layer 3",
            "backend.app.decision.safety_governor.check_action_safety",
            requires_safety_check=True,
        ),
        "build_carbon_aware_plan": tool_spec(
            "build_carbon_aware_plan",
            "Generate a carbon-aware operating schedule.",
            "carbon",
            "Layer 3",
            "backend.app.decision.carbon_scheduler.build_carbon_aware_plan",
        ),
        "get_action_bundle_schema": tool_spec(
            "get_action_bundle_schema",
            "Return the action bundle contract expected from future LLM planners.",
            "validation",
            "Layer 4",
            "backend.app.cognitive.action_bundle_schema.get_action_bundle_schema",
        ),
        "validate_action_bundle": tool_spec(
            "validate_action_bundle",
            "Validate an LLM-proposed action bundle against schema and basic bounds.",
            "validation",
            "Layer 4",
            "backend.app.cognitive.action_bundle_schema.validate_action_bundle",
            requires_safety_check=True,
        ),
        "generate_candidate_action_bundles": tool_spec(
            "generate_candidate_action_bundles",
            "Generate candidate action bundles using mock/optional LLM plus guardrails.",
            "llm_candidate_generation",
            "Layer 4",
            "backend.app.cognitive.candidate_bundle_generator.generate_candidate_action_bundles",
            implemented=True,
            allowed_for_llm=True,
            can_execute_action=False,
            requires_safety_check=False,
            notes=["Generates candidate bundles only; does not execute."],
        ),
        "get_relevant_knowledge_context": tool_spec(
            "get_relevant_knowledge_context",
            "Return Knowledge Graph context relevant to a goal and event.",
            "knowledge_graph",
            "Layer 4",
            "backend.app.cognitive.knowledge_graph.get_relevant_knowledge_context",
            implemented=True,
            allowed_for_llm=True,
            can_execute_action=False,
        ),
        "run_cognitive_operator": tool_spec(
            "run_cognitive_operator",
            "Run the controlled cognitive MCP tool-calling operator.",
            "cognitive_operator",
            "Layer 4",
            "backend.app.cognitive.cognitive_operator.run_cognitive_operator",
            implemented=True,
            allowed_for_llm=True,
            can_execute_action=False,
        ),
        "simulate_action_bundle": tool_spec(
            "simulate_action_bundle",
            "Future EnergyPlus simulation wrapper for candidate bundles.",
            "future_simulation",
            "Layer 5",
            "future.simulate_action_bundle",
            implemented=False,
            allowed_for_llm=False,
            notes=["EnergyPlus simulation will be implemented in Layer 5."],
        ),
        "compare_candidate_bundles": tool_spec(
            "compare_candidate_bundles",
            "Future comparison tool for simulated candidate bundles.",
            "future_rl",
            "Layer 5",
            "future.compare_candidate_bundles",
            implemented=False,
            allowed_for_llm=False,
        ),
        "select_best_bundle_with_rl": tool_spec(
            "select_best_bundle_with_rl",
            "Future RL selector for candidate action bundles.",
            "future_rl",
            "Layer 5",
            "future.select_best_bundle_with_rl",
            implemented=False,
            allowed_for_llm=False,
        ),
        "apply_approved_action_bundle": tool_spec(
            "apply_approved_action_bundle",
            "Future action execution tool.",
            "future_execution",
            "Layer 5",
            "future.apply_approved_action_bundle",
            read_only=False,
            implemented=False,
            can_execute_action=True,
            allowed_for_llm=False,
            notes=["Execution is disabled until Layer 5."],
        ),
        "record_execution_feedback_to_knowledge_graph": tool_spec(
            "record_execution_feedback_to_knowledge_graph",
            "Future execution feedback recorder for knowledge graph memory.",
            "future_memory",
            "Layer 5",
            "future.record_execution_feedback_to_knowledge_graph",
            implemented=False,
            allowed_for_llm=False,
        ),
    }


def list_mcp_tools() -> list[dict]:
    return [to_dict(spec) for spec in get_registered_mcp_tools().values()]


def get_mcp_tool_spec(tool_name: str) -> dict:
    spec = get_registered_mcp_tools().get(tool_name)
    return to_dict(spec) if spec else {}


def is_tool_allowed_for_llm(tool_name: str) -> bool:
    spec = get_registered_mcp_tools().get(tool_name)
    if not spec:
        return False
    return spec.implemented and spec.allowed_for_llm and not spec.can_execute_action


def execute_mcp_tool(tool_name: str, args: dict | None = None) -> dict:
    spec = get_registered_mcp_tools().get(tool_name)
    if not spec:
        return {
            "tool_name": tool_name,
            "success": False,
            "allowed": False,
            "result": None,
            "error": "Tool is not registered.",
        }

    allowed = is_tool_allowed_for_llm(tool_name)
    if not allowed:
        return {
            "tool_name": tool_name,
            "success": False,
            "allowed": False,
            "result": None,
            "error": "Tool is not implemented, not allowed for LLM use, or can execute actions.",
        }

    wrappers = {
        "get_building_intelligence_package": mcp_tool_wrappers.tool_get_building_intelligence_package,
        "get_dashboard_summary": mcp_tool_wrappers.tool_get_dashboard_summary,
        "get_autonomous_decision": mcp_tool_wrappers.tool_get_autonomous_decision,
        "get_dashboard_ready_decision": mcp_tool_wrappers.tool_get_dashboard_ready_decision,
        "run_multi_agent_supervisor": mcp_tool_wrappers.tool_run_multi_agent_supervisor,
        "check_action_safety": mcp_tool_wrappers.tool_check_action_safety,
        "build_carbon_aware_plan": mcp_tool_wrappers.tool_build_carbon_aware_plan,
        "get_action_bundle_schema": mcp_tool_wrappers.tool_get_action_bundle_schema,
        "validate_action_bundle": mcp_tool_wrappers.tool_validate_action_bundle,
        "generate_candidate_action_bundles": mcp_tool_wrappers.tool_generate_candidate_action_bundles,
        "get_relevant_knowledge_context": mcp_tool_wrappers.tool_get_relevant_knowledge_context,
        "run_cognitive_operator": mcp_tool_wrappers.tool_run_cognitive_operator,
    }
    wrapper = wrappers.get(tool_name)
    if not wrapper:
        return {
            "tool_name": tool_name,
            "success": False,
            "allowed": allowed,
            "result": None,
            "error": "No wrapper is available for this tool.",
        }

    wrapper_result = wrapper(args)
    return {
        "tool_name": tool_name,
        "success": wrapper_result.get("success", False),
        "allowed": allowed,
        "result": wrapper_result.get("result"),
        "error": wrapper_result.get("error"),
    }


def get_layer4_guardrail_summary() -> dict:
    return {
        "llm_can_execute_actions": False,
        "energyplus_execution_enabled": False,
        "action_bundle_validation_enabled": True,
        "safety_governor_required": True,
        "future_layer5_execution_required": True,
        "guardrails": [
            "LLM cannot execute actions directly.",
            "LLM-generated bundles must pass schema validation.",
            "Safety Governor must approve actions before execution.",
            "EnergyPlus execution is disabled until Layer 5.",
            "Unsafe or invalid tool calls return errors instead of executing.",
            "Fallback mode is required when candidate generation or simulation fails.",
        ],
    }
