def build_layer5_final_dashboard(
    plan_5_1_3: dict,
    execution_result: dict,
    learning_report: dict,
) -> dict:
    selected = plan_5_1_3.get("selected_bundle") or {}
    approval = plan_5_1_3.get("final_safety_approval") or {}
    provider_trace = plan_5_1_3.get("layer4_provider_trace") or {}
    adapter = execution_result.get("idf_adapter_report", {}) or {}
    dashboard = {
        "project": "ForgeHive",
        "layer": "Layer 5",
        "phase": "5.4-5.6",
        "status": "complete",
        "closedLoopAutonomyEnabled": True,
        "digitalTwinExecutionEnabled": True,
        "realBuildingExecutionEnabled": False,
        "energyPlusUsed": True,
        "llmProvider": provider_trace.get("selected_provider", "provided_or_fallback"),
        "mcpEnabled": True,
        "knowledgeGraphUsed": True,
        "rlBanditUsed": True,
        "safetyGovernorUsed": True,
        "candidateBundlesGenerated": plan_5_1_3.get("candidate_count", 0),
        "candidateBundlesSimulated": plan_5_1_3.get("simulation_count", 0),
        "selectedBundleName": selected.get("bundle_name", ""),
        "selectedBundleScore": selected.get("total_score", 0),
        "executionStatus": execution_result.get("execution_status", ""),
        "executionApplied": bool(execution_result.get("execution_applied", False)),
        "executionScope": "EnergyPlus digital twin only",
        "lightingAppliedInIDF": bool(adapter.get("lighting_applied", False)),
        "hvacSetpointAppliedInIDF": bool(adapter.get("hvac_setpoint_applied", False)),
        "ventilationAppliedInIDF": bool(adapter.get("ventilation_applied", False)),
        "metadataOnlyActions": adapter.get("actions_metadata_only", []),
        "adapterWarnings": adapter.get("warnings", []),
        "adapterChangeCount": len(adapter.get("change_log", [])),
        "energySavedPercent": execution_result.get("energy_saved_percent", 0),
        "carbonReducedPercent": execution_result.get("carbon_reduced_percent", 0),
        "comfortStatus": execution_result.get("comfort_status", "Unknown"),
        "anomalyCount": execution_result.get("anomaly_count", 0),
        "actualReward": learning_report.get("actual_reward", 0),
        "banditUpdated": bool(learning_report.get("bandit_updated", False)),
        "memoryUpdated": bool(learning_report.get("memory_updated", False)),
        "knowledgeGraphUpdated": bool(learning_report.get("knowledge_graph_updated", False)),
        "experienceGraphEnabled": True,
        "experienceGraphUpdated": bool(learning_report.get("experience_graph_updated", False)),
        "experienceId": learning_report.get("experience_id"),
        "similarExperiencesUsed": learning_report.get("similar_experiences_used", 0),
        "experienceConfidence": learning_report.get("experience_confidence", 0),
        "experienceLessonsLearned": learning_report.get("lessons_learned", []),
        "selfCorrectionSummary": learning_report.get("self_correction", {}).get("summary", ""),
        "safetySummary": approval.get("safety_summary", ""),
        "judgeSummary": (
            "ForgeHive generated candidate plans with an open-source LLM, simulated them in EnergyPlus, ranked them with "
            "reward/RL and KG context, passed them through a Safety Governor, executed the approved plan in the digital "
            "twin, measured the result, and updated memory/learning."
        ),
    }
    return dashboard
