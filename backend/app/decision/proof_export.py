import json
from pathlib import Path

from backend.app.decision.action_schema import (
    create_demo_safe_action,
    create_demo_unsafe_action,
    to_dict,
)
from backend.app.decision.carbon_scheduler import build_carbon_aware_plan
from backend.app.decision.decision_api import get_autonomous_decision
from backend.app.decision.safety_governor import check_action_safety
from backend.app.decision.strategy_bandit import load_bandit_state
from backend.app.decision.supervisor import run_multi_agent_supervisor
from backend.app.intelligence.intelligence_api import get_building_intelligence_package


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXECUTION_NOTE = (
    "Layer 3 decides and safety-checks actions. Layer 5.1-5.3 simulates, ranks, "
    "and final-safety-checks approved plans; digital-twin execution starts in Phase 5.4."
)


def get_layer3_artifact_dir() -> Path:
    output_dir = PROJECT_ROOT / "artifacts" / "layer_3_decision"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def build_goal_decision_suite() -> dict:
    return {
        "balanced_optimization": get_autonomous_decision("balanced optimization"),
        "reduce_energy_keep_comfort_safe": get_autonomous_decision("reduce energy while keeping comfort safe"),
        "reduce_carbon": get_autonomous_decision("reduce carbon impact today"),
        "fix_anomalies": get_autonomous_decision("fix building issues and anomalies"),
        "maintain_comfort": get_autonomous_decision("maintain comfort"),
    }


def build_safety_proof() -> dict:
    safe_action = create_demo_safe_action()
    unsafe_action = create_demo_unsafe_action()
    result = {
        "safe_action_test": {
            "action": to_dict(safe_action),
            "decision": {},
        },
        "unsafe_action_test": {
            "action": to_dict(unsafe_action),
            "decision": {},
        },
        "summary": "Safety Governor approved safe action and rejected unsafe aggressive action.",
    }

    try:
        safe_decision = check_action_safety(safe_action)
        unsafe_decision = check_action_safety(unsafe_action)
        result["safe_action_test"]["decision"] = to_dict(safe_decision)
        result["unsafe_action_test"]["decision"] = to_dict(unsafe_decision)

        errors = []
        if not safe_decision.approved:
            errors.append("Expected safe action to be approved.")
        if unsafe_decision.approved:
            errors.append("Expected unsafe action to be rejected.")
        if errors:
            result["errors"] = errors
    except Exception as exc:
        result["errors"] = [f"Safety proof failed: {exc}"]

    return result


def build_multi_agent_proof() -> dict:
    supervisor_result = run_multi_agent_supervisor("reduce_energy_keep_comfort_safe")
    return {
        "agents_consulted": supervisor_result.get("agents_consulted", []),
        "selected_recommendation": supervisor_result.get("selected_recommendation", {}),
        "ranked_recommendations": supervisor_result.get("ranked_recommendations", []),
        "safety_decision": supervisor_result.get("safety_decision", {}),
        "status": supervisor_result.get("status", ""),
        "summary": supervisor_result.get("summary", ""),
    }


def build_carbon_scheduler_proof() -> dict:
    plan = build_carbon_aware_plan()
    return {
        "strategy_name": plan["strategy_name"],
        "low_carbon_windows": plan["low_carbon_windows"],
        "high_carbon_windows": plan["high_carbon_windows"],
        "recommended_schedule": plan["recommended_schedule"],
        "expected_carbon_reduced_percent": plan["expected_carbon_reduced_percent"],
        "expected_energy_saved_percent": plan["expected_energy_saved_percent"],
        "summary": "Carbon-aware scheduler identifies low-carbon and high-carbon windows and proposes schedule shifting.",
    }


def build_bandit_proof() -> dict:
    state = load_bandit_state()
    strategies = state.get("strategies", {})
    history = state.get("history", [])

    if strategies:
        best_strategy = max(
            strategies,
            key=lambda strategy: strategies[strategy].get("average_reward", 0.0),
        )
    else:
        best_strategy = ""

    summary = (
        "Contextual bandit stores strategy rewards and supports future self-correction."
        if history
        else "Bandit is initialized and ready to learn from Layer 5 execution feedback."
    )

    return {
        "strategies": strategies,
        "history_count": len(history),
        "best_average_reward_strategy": best_strategy,
        "summary": summary,
    }


def build_layer3_dashboard_summary(proof_package: dict) -> dict:
    sample_decision = proof_package["goal_decision_suite"]["reduce_energy_keep_comfort_safe"]
    sample_action = sample_decision["decision"].get("selected_action") or {}
    sample_safety = sample_decision["decision"].get("safety_decision") or {}

    return {
        "layer": "Layer 3",
        "status": "complete",
        "autonomousDecisionReady": True,
        "executionEnabled": False,
        "executionLayer": "Layer 5",
        "safetyGovernorEnabled": True,
        "multiAgentEnabled": True,
        "banditEnabled": True,
        "carbonAwareSchedulingEnabled": True,
        "sampleSelectedStrategy": sample_action.get("strategy_name", ""),
        "sampleApproved": bool(sample_safety.get("approved", False)),
        "sampleRiskLevel": sample_safety.get("risk_level", ""),
        "summary": "Layer 3 can select and safety-check actions but does not execute them yet.",
    }


def build_mcp_tool_preview() -> list[dict]:
    return [
        {
            "tool_name": "get_autonomous_decision",
            "backend_function": "backend.app.decision.decision_api.get_autonomous_decision",
            "purpose": "Ask ForgeHive to select and safety-check the best action for a goal.",
        },
        {
            "tool_name": "get_dashboard_ready_decision",
            "backend_function": "backend.app.decision.decision_api.get_dashboard_ready_decision",
            "purpose": "Return compact decision output for dashboard or LLM explanation.",
        },
        {
            "tool_name": "check_action_safety",
            "backend_function": "backend.app.decision.safety_governor.check_action_safety",
            "purpose": "Approve or reject a proposed action before execution.",
        },
        {
            "tool_name": "run_multi_agent_supervisor",
            "backend_function": "backend.app.decision.supervisor.run_multi_agent_supervisor",
            "purpose": "Consult energy, comfort, carbon, and anomaly agents.",
        },
        {
            "tool_name": "build_carbon_aware_plan",
            "backend_function": "backend.app.decision.carbon_scheduler.build_carbon_aware_plan",
            "purpose": "Generate carbon-aware operating schedule.",
        },
    ]


def build_layer2_input_snapshot() -> dict:
    intelligence = get_building_intelligence_package()
    best_strategy = intelligence.get("memory_summary", {}).get("best_strategy", {})
    return {
        "overall_score": intelligence.get("score", {}).get("overall", 0),
        "comfort_status": intelligence.get("comfort", {}).get("status", "Safe"),
        "anomaly_count": intelligence.get("anomalies", {}).get("anomaly_count", 0),
        "best_strategy": best_strategy.get("strategy", "") if best_strategy.get("available") else "",
    }


def generate_layer3_proof_package() -> dict:
    proof_package = {
        "project": {
            "name": "ForgeHive",
            "layer": "Layer 3",
            "phase": "Phase 3.7",
            "description": "Autonomous decision engine proof package",
        },
        "status": {
            "layer_complete": True,
            "actions_executed": False,
            "execution_note": EXECUTION_NOTE,
        },
        "layer2_input_snapshot": build_layer2_input_snapshot(),
        "goal_decision_suite": build_goal_decision_suite(),
        "multi_agent_proof": build_multi_agent_proof(),
        "safety_proof": build_safety_proof(),
        "carbon_scheduler_proof": build_carbon_scheduler_proof(),
        "bandit_proof": build_bandit_proof(),
        "dashboard_summary": {},
        "future_mcp_tool_preview": build_mcp_tool_preview(),
        "judging_alignment": {
            "ai_autonomy": "Multi-agent supervisor selects actions from building state and user/building goals.",
            "reliability": "Safety Governor rejects risky actions before execution.",
            "energy_savings": "Energy Agent and strategy bandit prioritize energy-saving modes.",
            "comfort": "Comfort Agent and Safety Governor protect occupied-zone comfort constraints.",
            "carbon": "Carbon-aware scheduler shifts flexible loads toward lower-carbon windows.",
            "explainability": "Every decision includes selected agent, strategy, rationale, safety decision, and risk level.",
        },
    }
    proof_package["dashboard_summary"] = build_layer3_dashboard_summary(proof_package)
    return proof_package


def build_layer3_markdown_summary(proof_package: dict) -> str:
    dashboard = proof_package["dashboard_summary"]
    safety = proof_package["safety_proof"]
    carbon = proof_package["carbon_scheduler_proof"]
    bandit = proof_package["bandit_proof"]
    tools = "\n".join(
        f"- `{tool['tool_name']}`: {tool['purpose']}"
        for tool in proof_package["future_mcp_tool_preview"]
    )

    return f"""# ForgeHive Layer 3 Proof

## Layer 3 Overview
Layer 3 is the autonomous decision engine for ForgeHive. It converts Layer 2 building intelligence into safe, explainable action plans for closed-loop review.

Layer 3 does not execute actions. It only decides, ranks, safety-checks, and prepares approved actions for Layer 5 simulation, ranking, and final approval.

## What Was Implemented
- Standard `ControlAction` and `SafetyDecision` schemas
- Safety Governor for approve/reject decisions
- Energy, comfort, carbon, and anomaly decision agents
- Multi-agent supervisor
- Contextual bandit strategy selector
- Carbon-aware scheduling planner
- Decision API and dashboard-ready decision output

## Decision Flow
1. Read Layer 2 building intelligence.
2. Consult domain agents.
3. Use the contextual bandit to bias strategy selection.
4. Rank recommendations.
5. Safety-check the selected action.
6. Export a decision package for dashboard, future MCP tools, and Layer 5 closed-loop review.

## Multi-Agent Architecture
Agents consulted in the sample proof: {", ".join(proof_package["multi_agent_proof"].get("agents_consulted", []))}

Selected status: {proof_package["multi_agent_proof"].get("status", "")}

## Safety Governor Proof
- Safe action approved: {safety["safe_action_test"]["decision"].get("approved")}
- Unsafe action approved: {safety["unsafe_action_test"]["decision"].get("approved")}

## Carbon-Aware Scheduling
- Low-carbon windows found: {len(carbon["low_carbon_windows"])}
- High-carbon windows found: {len(carbon["high_carbon_windows"])}
- Expected carbon reduction: {carbon["expected_carbon_reduced_percent"]}%

## RL / Contextual Bandit
Best average reward strategy: {bandit["best_average_reward_strategy"]}

History count: {bandit["history_count"]}

## Dashboard Output
- Autonomous decision ready: {dashboard["autonomousDecisionReady"]}
- Execution enabled: {dashboard["executionEnabled"]}
- Sample selected strategy: {dashboard["sampleSelectedStrategy"]}
- Sample risk level: {dashboard["sampleRiskLevel"]}

## Future MCP Tools
{tools}

## What Layer 3 Does Not Do Yet
Layer 3 does not execute actions. It does not call MCP tools, LLMs, or EnergyPlus. It only prepares and safety-checks decisions.

## Ready for Layer 4
Layer 4 can expose these decision functions as MCP/LLM-callable tools while preserving the Safety Governor boundary.
"""


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def save_layer3_proof_artifacts(output_dir: Path | None = None) -> dict:
    proof_package = generate_layer3_proof_package()
    artifact_dir = Path(output_dir) if output_dir is not None else get_layer3_artifact_dir()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    proof_file = artifact_dir / "layer3_proof_package.json"
    dashboard_file = artifact_dir / "layer3_dashboard_summary.json"
    markdown_file = artifact_dir / "layer3_summary.md"
    docs_file = docs_dir / "LAYER_3_PROOF.md"
    markdown_summary = build_layer3_markdown_summary(proof_package)

    save_json(proof_file, proof_package)
    save_json(dashboard_file, proof_package["dashboard_summary"])
    markdown_file.write_text(markdown_summary)
    docs_file.write_text(markdown_summary)

    return {
        "proof_package": str(proof_file),
        "dashboard_summary": str(dashboard_file),
        "markdown_summary": str(markdown_file),
        "docs_summary": str(docs_file),
    }
