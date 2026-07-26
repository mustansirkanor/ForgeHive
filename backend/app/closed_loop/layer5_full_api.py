from backend.app.closed_loop.closed_loop_dashboard import build_layer5_final_dashboard
from backend.app.closed_loop.digital_twin_executor import execute_approved_bundle_in_digital_twin
from backend.app.closed_loop.feedback_learner import learn_from_execution
from backend.app.closed_loop.layer5_api import run_layer5_phase_1_3_closed_loop
from backend.app.closed_loop.proof_export import export_layer5_full_closed_loop_proof


def run_layer5_full_closed_loop(
    user_message: str = "The meeting room is empty now. Save energy but keep comfort safe.",
    candidate_bundles: list[dict] | None = None,
    use_layer4_operator: bool = True,
    layer4_output_override: dict | None = None,
) -> dict:
    plan_5_1_3 = {}
    execution_result = {}
    learning_report = {}
    dashboard = {}
    artifacts = {}
    error = None

    try:
        plan_5_1_3 = run_layer5_phase_1_3_closed_loop(
            user_message=user_message,
            candidate_bundles=candidate_bundles,
            use_layer4_operator=use_layer4_operator,
            layer4_output_override=layer4_output_override,
        )
        execution_result = execute_approved_bundle_in_digital_twin(plan_5_1_3)
        learning_report = learn_from_execution(plan_5_1_3, execution_result)
        dashboard = build_layer5_final_dashboard(plan_5_1_3, execution_result, learning_report)
        artifacts = export_layer5_full_closed_loop_proof(plan_5_1_3, execution_result, learning_report, dashboard)
    except Exception as exc:
        error = str(exc)

    artifacts_exported = bool((artifacts.get("generated_files") or {}))
    execution_succeeded = execution_result.get("execution_status") == "executed" and execution_result.get("execution_applied") is True
    closed_loop_complete = bool(plan_5_1_3 and execution_result and learning_report and dashboard and artifacts_exported and execution_succeeded)
    experience_graph = {
        "experience_graph_updated": bool(learning_report.get("experience_graph_updated", False)),
        "experience_id": learning_report.get("experience_id"),
        "similar_experiences_used": learning_report.get("similar_experiences_used", 0),
        "experience_confidence": learning_report.get("experience_confidence", 0),
        "lessons_learned": learning_report.get("lessons_learned", []),
        "real_building_execution": False,
    }

    return {
        "project": {
            "name": "ForgeHive",
            "layer": "Layer 5",
            "phase": "5.4-5.6",
        },
        "user_message": user_message,
        "phase_5_1_3_plan": plan_5_1_3,
        "phase_5_4_execution": execution_result,
        "phase_5_5_learning": learning_report,
        "phase_5_6_dashboard": dashboard,
        "artifact_paths": artifacts,
        "closed_loop_complete": closed_loop_complete,
        "real_building_execution": False,
        "digital_twin_execution": execution_succeeded,
        "experience_graph": experience_graph,
        "experience_graph_updated": experience_graph["experience_graph_updated"],
        "experience_id": experience_graph["experience_id"],
        "summary": (
            "Layer 5 full closed loop completed successfully inside the EnergyPlus digital twin."
            if closed_loop_complete
            else "Layer 5 full closed loop returned a safe graceful result; digital twin execution may have been blocked or failed."
        ),
        "error": error,
    }
