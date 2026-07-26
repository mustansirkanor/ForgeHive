import json
from pathlib import Path

from backend.app.decision.action_planner import build_action_plan, normalize_goal
from backend.app.intelligence.intelligence_api import get_building_intelligence_package


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "layer_3_decision"
NOTES = [
    "Layer 3 decides and safety-checks actions.",
    "Layer 5.1-5.3 simulates, ranks, and final-safety-checks approved plans before any execution phase.",
]


def get_building_context(intelligence: dict) -> dict:
    best_strategy = intelligence.get("memory_summary", {}).get("best_strategy", {})
    return {
        "overall_score": intelligence.get("score", {}).get("overall", 0),
        "comfort_status": intelligence.get("comfort", {}).get("status", "Safe"),
        "anomaly_count": intelligence.get("anomalies", {}).get("anomaly_count", 0),
        "best_strategy": best_strategy.get("strategy", "") if best_strategy.get("available") else "",
    }


def get_autonomous_decision(goal: str | None = None) -> dict:
    normalized_goal = normalize_goal(goal)
    intelligence = get_building_intelligence_package()
    action_plan = build_action_plan(normalized_goal, intelligence)

    return {
        "project": {
            "name": "ForgeHive",
            "layer": "Layer 3",
            "phase": "Phase 3.6",
            "description": "Autonomous decision API",
        },
        "input_goal": goal,
        "normalized_goal": normalized_goal,
        "building_context": get_building_context(intelligence),
        "decision": {
            "selected_plan_type": action_plan["selected_plan_type"],
            "selected_action": action_plan["selected_action"],
            "safety_decision": action_plan["safety_decision"],
            "ready_for_execution": action_plan["ready_for_execution"],
            "summary": action_plan["summary"],
        },
        "supporting_outputs": {
            "supervisor_decision": action_plan["supervisor_decision"],
            "carbon_plan": action_plan["carbon_plan"],
        },
        "notes": NOTES,
    }


def get_dashboard_ready_decision(goal: str | None = None) -> dict:
    decision = get_autonomous_decision(goal)
    selected_action = decision["decision"].get("selected_action") or {}
    safety_decision = decision["decision"].get("safety_decision") or {}

    return {
        "goal": decision["normalized_goal"],
        "selectedStrategy": selected_action.get("strategy_name", ""),
        "actionType": selected_action.get("action_type", ""),
        "approved": bool(safety_decision.get("approved", False)),
        "riskLevel": safety_decision.get("risk_level", ""),
        "readyForExecution": bool(decision["decision"].get("ready_for_execution", False)),
        "summary": decision["decision"].get("summary", ""),
    }


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def save_decision_artifacts(goal: str | None = None, output_dir: Path | None = None) -> dict:
    output_path = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path.mkdir(parents=True, exist_ok=True)

    autonomous_file = output_path / "autonomous_decision.json"
    dashboard_file = output_path / "dashboard_decision.json"

    save_json(autonomous_file, get_autonomous_decision(goal))
    save_json(dashboard_file, get_dashboard_ready_decision(goal))

    return {
        "output_dir": str(output_path),
        "generated_files": {
            "autonomous_decision": str(autonomous_file),
            "dashboard_decision": str(dashboard_file),
        },
    }
