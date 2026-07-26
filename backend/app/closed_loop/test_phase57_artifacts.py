import json
from pathlib import Path

from backend.app.closed_loop.phase57_artifacts import (
    build_phase57_dashboard_summary,
    export_phase57_artifacts,
)


def demo_result(provider: str = "ollama", executed: bool = True) -> dict:
    execution_status = "executed" if executed else "failed"
    return {
        "project": "ForgeHive",
        "phase": "5.7",
        "demo_type": "real_ollama_full_loop",
        "selected_provider": provider,
        "model": "llama3.1:8b",
        "fallback_used": False,
        "candidate_count": 1,
        "candidate_bundles": [{"bundle_name": "artifact_test_bundle", "actions": []}],
        "layer5_result": {
            "phase_5_1_3_plan": {"simulation_count": 1},
            "phase_5_4_execution": {
                "execution_status": execution_status,
                "execution_applied": executed,
                "idf_adapter_report": {
                    "lighting_applied": True,
                    "hvac_setpoint_applied": True,
                    "ventilation_applied": True,
                    "actions_metadata_only": [{"action_type": "ventilation_adjustment"}],
                    "warnings": ["No safely editable ventilation object found in this IDF."],
                    "change_log": [
                        {"action_type": "lighting_adjustment"},
                        {"action_type": "hvac_setpoint_adjustment"},
                        {"action_type": "ventilation_adjustment"},
                    ],
                },
                "energy_saved_percent": 5.0,
                "carbon_reduced_percent": 5.0,
                "comfort_status": "Safe",
            },
            "phase_5_5_learning": {
                "memory_updated": executed,
                "bandit_updated": executed,
                "knowledge_graph_updated": executed,
            },
            "phase_5_6_dashboard": {
                "safetyGovernorUsed": True,
                "rlBanditUsed": True,
                "knowledgeGraphUsed": True,
            },
        },
        "digital_twin_execution": executed,
        "real_building_execution": False,
        "energy_saved_percent": 5.0,
        "carbon_reduced_percent": 5.0,
        "comfort_status": "Safe",
        "bandit_updated": executed,
        "memory_updated": executed,
        "knowledge_graph_updated": executed,
        "closed_loop_complete": executed,
        "idf_adapter_summary": {
            "lighting_applied": False,
            "hvac_setpoint_applied": False,
            "ventilation_applied": False,
            "metadata_only_actions": [],
            "warnings": [],
            "change_log": [],
            "adapter_change_count": 0,
        },
        "judge_summary": "Test summary.",
    }


if __name__ == "__main__":
    output = export_phase57_artifacts(demo_result())
    print(json.dumps(output, indent=2))
    files = output["generated_files"]
    for path in files.values():
        assert Path(path).exists()

    dashboard = output["dashboard_summary"]
    assert dashboard["lightingAppliedInIDF"] is True
    assert dashboard["hvacSetpointAppliedInIDF"] is True
    assert dashboard["ventilationAppliedInIDF"] is True
    assert "metadataOnlyActions" in dashboard
    assert dashboard["adapterWarnings"] == ["No safely editable ventilation object found in this IDF."]
    assert dashboard["adapterChangeCount"] == 3
    assert dashboard["judgeReady"] is True
    assert dashboard["lightingAppliedInIDF"] == demo_result()["layer5_result"]["phase_5_4_execution"]["idf_adapter_report"]["lighting_applied"]
    assert dashboard["hvacSetpointAppliedInIDF"] == demo_result()["layer5_result"]["phase_5_4_execution"]["idf_adapter_report"]["hvac_setpoint_applied"]
    assert dashboard["ventilationAppliedInIDF"] == demo_result()["layer5_result"]["phase_5_4_execution"]["idf_adapter_report"]["ventilation_applied"]

    mock_dashboard = build_phase57_dashboard_summary(demo_result("mock", True), artifacts_exported=True)
    assert mock_dashboard["judgeReady"] is False
    failed_dashboard = build_phase57_dashboard_summary(demo_result("ollama", False), artifacts_exported=True)
    assert failed_dashboard["judgeReady"] is False
    json.dumps(output)

    print("\nPhase 5.7 artifact export test passed.")
