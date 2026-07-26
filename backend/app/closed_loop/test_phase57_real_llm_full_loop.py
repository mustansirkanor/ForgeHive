import json
import os
from pathlib import Path

from backend.app.closed_loop.real_llm_full_loop import (
    ollama_is_reachable,
    openrouter_key_present,
    run_real_ollama_full_loop_demo,
)


if __name__ == "__main__":
    ollama_available = ollama_is_reachable()
    openrouter_available = openrouter_key_present()
    require_real = os.environ.get("FORGEHIVE_REQUIRE_REAL_LLM_DEMO", "").lower() == "true"

    if not ollama_available and not openrouter_available:
        message = "Real provider unavailable; strict real LLM demo not proven."
        print(message)
        if require_real:
            raise AssertionError(message)
    else:
        output = run_real_ollama_full_loop_demo()
        print(json.dumps(output, indent=2))

        if ollama_available:
            assert output["selected_provider"] == "ollama"
            assert output["fallback_used"] is False
        else:
            assert output["selected_provider"] == "openrouter"
            assert output["fallback_used"] in {True, False}
            assert output["attempted_providers"]

        assert output["candidate_count"] > 0
        assert output["energyplus_executed"] is True
        assert output["digital_twin_execution"] is True
        assert output["real_building_execution"] is False
        assert output["experience_graph_updated"] is True
        assert output["experience_id"]
        assert output["experience_graph"]
        assert output["experience_graph"]["real_building_execution"] is False
        assert output["idf_adapter_summary"]

        dashboard = output["layer5_result"]["phase_5_6_dashboard"]
        assert dashboard["safetyGovernorUsed"] is True
        assert dashboard["rlBanditUsed"] is True
        assert dashboard["knowledgeGraphUsed"] is True

        artifacts = output.get("artifact_paths", {}).get("generated_files", {})
        assert artifacts
        for path in artifacts.values():
            assert Path(path).exists()
        phase57_dashboard = output["phase57_dashboard_summary"]
        adapter = output["idf_adapter_summary"]
        assert phase57_dashboard["lightingAppliedInIDF"] == adapter["lighting_applied"]
        assert phase57_dashboard["hvacSetpointAppliedInIDF"] == adapter["hvac_setpoint_applied"]
        assert phase57_dashboard["ventilationAppliedInIDF"] == adapter["ventilation_applied"]
        assert phase57_dashboard["metadataOnlyActions"] == adapter["metadata_only_actions"]
        assert phase57_dashboard["adapterWarnings"] == adapter["warnings"]
        assert phase57_dashboard["adapterChangeCount"] == adapter["adapter_change_count"]
        assert phase57_dashboard["realBuildingExecution"] is False
        if output["energyplus_executed"]:
            assert phase57_dashboard["digitalTwinExecution"] is True
        assert phase57_dashboard["judgeReady"] is True

    print("\nPhase 5.7 real LLM full-loop smoke test completed.")
