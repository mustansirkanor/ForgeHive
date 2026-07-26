from backend.app.cognitive.action_bundle_schema import (
    get_action_bundle_schema,
    to_dict as bundle_to_dict,
    validate_action_bundle,
)
from backend.app.decision.action_schema import (
    ControlAction,
    create_demo_safe_action,
    create_demo_unsafe_action,
    to_dict,
)
from backend.app.decision.carbon_scheduler import build_carbon_aware_plan
from backend.app.decision.decision_api import (
    get_autonomous_decision,
    get_dashboard_ready_decision,
)
from backend.app.decision.safety_governor import check_action_safety
from backend.app.decision.supervisor import run_multi_agent_supervisor
from backend.app.intelligence.intelligence_api import (
    get_building_intelligence_package,
    get_dashboard_ready_intelligence,
)


def build_tool_error(tool_name: str, error: Exception | str) -> dict:
    return {
        "tool_name": tool_name,
        "success": False,
        "error": str(error),
    }


def build_tool_success(tool_name: str, result) -> dict:
    return {
        "tool_name": tool_name,
        "success": True,
        "result": result,
    }


def tool_get_building_intelligence_package(args=None) -> dict:
    tool_name = "get_building_intelligence_package"
    try:
        return build_tool_success(tool_name, get_building_intelligence_package())
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_get_dashboard_summary(args=None) -> dict:
    tool_name = "get_dashboard_summary"
    try:
        return build_tool_success(tool_name, get_dashboard_ready_intelligence())
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_get_autonomous_decision(args=None) -> dict:
    tool_name = "get_autonomous_decision"
    try:
        args = args or {}
        return build_tool_success(tool_name, get_autonomous_decision(args.get("goal")))
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_get_dashboard_ready_decision(args=None) -> dict:
    tool_name = "get_dashboard_ready_decision"
    try:
        args = args or {}
        return build_tool_success(tool_name, get_dashboard_ready_decision(args.get("goal")))
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_run_multi_agent_supervisor(args=None) -> dict:
    tool_name = "run_multi_agent_supervisor"
    try:
        args = args or {}
        return build_tool_success(
            tool_name,
            run_multi_agent_supervisor(args.get("goal", "balanced_optimization")),
        )
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_build_carbon_aware_plan(args=None) -> dict:
    tool_name = "build_carbon_aware_plan"
    try:
        return build_tool_success(tool_name, build_carbon_aware_plan())
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def action_from_args(args: dict) -> ControlAction:
    if args.get("demo") == "safe":
        return create_demo_safe_action()
    if args.get("demo") == "unsafe":
        return create_demo_unsafe_action()

    action = args.get("action")
    if not isinstance(action, dict):
        raise ValueError("Provide {'demo': 'safe'}, {'demo': 'unsafe'}, or an action dict.")

    return ControlAction(
        action_id=action.get("action_id", "llm_proposed_action"),
        strategy_name=action.get("strategy_name", "llm_proposed_strategy"),
        action_type=action["action_type"],
        target=action.get("target", ""),
        description=action.get("description", ""),
        parameters=action.get("parameters", {}),
        expected_energy_saved_percent=float(action.get("expected_energy_saved_percent", 0.0)),
        expected_carbon_reduced_percent=float(action.get("expected_carbon_reduced_percent", 0.0)),
        expected_comfort_impact=action.get("expected_comfort_impact", "neutral"),
        source_agent=action.get("source_agent", "llm_candidate"),
        priority=action.get("priority", "medium"),
    )


def tool_check_action_safety(args=None) -> dict:
    tool_name = "check_action_safety"
    try:
        args = args or {}
        action = action_from_args(args)
        decision = check_action_safety(action)
        return build_tool_success(tool_name, to_dict(decision))
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_validate_action_bundle(args=None) -> dict:
    tool_name = "validate_action_bundle"
    try:
        args = args or {}
        if "bundle" not in args:
            raise ValueError("Missing required 'bundle' argument.")
        result = validate_action_bundle(args["bundle"])
        return build_tool_success(tool_name, bundle_to_dict(result))
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_get_action_bundle_schema(args=None) -> dict:
    tool_name = "get_action_bundle_schema"
    try:
        return build_tool_success(tool_name, get_action_bundle_schema())
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_generate_candidate_action_bundles(args=None) -> dict:
    tool_name = "generate_candidate_action_bundles"
    try:
        from backend.app.cognitive.candidate_bundle_generator import generate_candidate_action_bundles

        args = args or {}
        return build_tool_success(
            tool_name,
            generate_candidate_action_bundles(
                goal=args.get("goal", "balanced_optimization"),
                event_type=args.get("event_type", "operator_request"),
                extra_context=args.get("extra_context"),
                max_bundles=args.get("max_bundles", 5),
            ),
        )
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_get_relevant_knowledge_context(args=None) -> dict:
    tool_name = "get_relevant_knowledge_context"
    try:
        from backend.app.cognitive.knowledge_graph import get_relevant_knowledge_context

        args = args or {}
        return build_tool_success(
            tool_name,
            get_relevant_knowledge_context(
                args.get("goal", "balanced_optimization"),
                args.get("event_type", "operator_request"),
                args.get("building_context", {}),
            ),
        )
    except Exception as exc:
        return build_tool_error(tool_name, exc)


def tool_run_cognitive_operator(args=None) -> dict:
    tool_name = "run_cognitive_operator"
    try:
        from backend.app.cognitive.cognitive_operator import run_cognitive_operator

        args = args or {}
        return build_tool_success(
            tool_name,
            run_cognitive_operator(
                args.get("user_input", ""),
                args.get("extra_context"),
            ),
        )
    except Exception as exc:
        return build_tool_error(tool_name, exc)
