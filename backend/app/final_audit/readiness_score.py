import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "final_submission"
OUTPUT_FILE = OUTPUT_DIR / "forgehive_readiness_score.json"


def grade_for_score(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Needs Work"
    return "Not Ready"


def bool_points(condition: bool, points: float) -> float:
    return points if condition else 0.0


def calculate_forgehive_readiness_score(test_matrix: dict, artifact_audit: dict, demo_audit: dict) -> dict:
    strengths = []
    risks = []
    recommended_next_actions = []

    total_tests = max(int(test_matrix.get("total_tests", 0) or 0), 1)
    passed_tests = int(test_matrix.get("passed_tests", 0) or 0)
    skipped_tests = int(test_matrix.get("skipped_tests", 0) or 0)
    test_pass_rate = (passed_tests + (0.5 * skipped_tests)) / total_tests
    test_points = min(30.0, max(0.0, test_pass_rate * 30.0))

    required = max(int(artifact_audit.get("required_file_count", 0) or 0), 1)
    existing = int(artifact_audit.get("existing_file_count", 0) or 0)
    artifact_points = min(20.0, (existing / required) * 20.0)
    if artifact_audit.get("invalid_json_files") or artifact_audit.get("warnings"):
        artifact_points = max(0.0, artifact_points - 5.0)

    demo = demo_audit.get("demo_result", {})
    dashboard = demo.get("phase57_dashboard_summary", {})
    adapter = demo.get("idf_adapter_summary", {})

    real_llm_points = bool_points(demo.get("selected_provider") in {"ollama", "openrouter"}, 15)
    energyplus_points = bool_points(demo.get("digital_twin_execution") is True and demo.get("energyplus_executed") is True, 15)
    safety_points = bool_points(
        demo.get("real_building_execution") is False
        and dashboard.get("realBuildingExecution") is False
        and dashboard.get("safetyGovernorUsed") is True,
        10,
    )
    learning_points = bool_points(
        any(bool(demo.get(key)) for key in ["memory_updated", "bandit_updated", "knowledge_graph_updated"]),
        5,
    )
    presentation_points = bool_points(dashboard.get("judgeReady") is True and artifact_audit.get("audit_passed") is True, 5)

    score = round(
        test_points
        + artifact_points
        + real_llm_points
        + energyplus_points
        + safety_points
        + learning_points
        + presentation_points,
        2,
    )

    if test_points >= 27:
        strengths.append("Automated test matrix is broadly passing.")
    else:
        risks.append("Some automated tests failed or were skipped.")
        recommended_next_actions.append("Inspect forgehive_test_matrix.json and fix failed modules before the final demo.")

    if artifact_audit.get("audit_passed"):
        strengths.append("Required proof artifacts are present and internally valid.")
    else:
        risks.append("Artifact audit found missing files, invalid JSON, or flag warnings.")
        recommended_next_actions.append("Regenerate missing layer proof artifacts and rerun Layer 6.")

    if real_llm_points:
        strengths.append(f"Final demo used real provider {demo.get('selected_provider')}.")
    else:
        risks.append("Final demo did not prove a real LLM provider.")
        recommended_next_actions.append("Start Ollama or configure OpenRouter, then rerun the final demo audit.")

    if energyplus_points:
        strengths.append("EnergyPlus digital twin execution completed.")
    else:
        risks.append("EnergyPlus digital twin execution did not complete.")
        recommended_next_actions.append("Inspect EnergyPlus run logs and IDF adapter output.")

    if safety_points:
        strengths.append("Safety Governor and no-real-building boundary are preserved.")
    else:
        risks.append("Safety or real-building execution flags need review.")
        recommended_next_actions.append("Verify realBuildingExecution remains false and Safety Governor is used.")

    if learning_points:
        strengths.append("Learning loop updated memory, bandit, or Knowledge Graph after execution.")
    else:
        risks.append("Learning updates were not proven.")
        recommended_next_actions.append("Inspect learning report and execution status.")

    if adapter.get("lighting_applied") and adapter.get("hvac_setpoint_applied") and adapter.get("ventilation_applied"):
        strengths.append("IDF adapter applied lighting, HVAC setpoint, and ventilation changes.")
    else:
        risks.append("Some IDF adapter actions were metadata-only or unavailable in the model.")

    result = {
        "score": score,
        "grade": grade_for_score(score),
        "passed": score >= 75,
        "strengths": strengths,
        "risks": risks,
        "recommended_next_actions": recommended_next_actions,
        "score_breakdown": {
            "test_pass_rate_points": round(test_points, 2),
            "artifact_completeness_points": round(artifact_points, 2),
            "real_llm_demo_points": real_llm_points,
            "energyplus_closed_loop_points": energyplus_points,
            "safety_guardrails_points": safety_points,
            "learning_loop_points": learning_points,
            "presentation_readiness_points": presentation_points,
        },
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    print(json.dumps(calculate_forgehive_readiness_score({}, {}, {}), indent=2))
