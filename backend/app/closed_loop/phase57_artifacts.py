import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "layer_5_closed_loop"


def dedupe_dicts(items: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for item in items:
        key = json.dumps(item, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def dedupe_strings(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def collect_idf_adapter_reports(demo_result: dict) -> list[dict]:
    layer5 = demo_result.get("layer5_result", {})
    reports = []
    execution_report = layer5.get("phase_5_4_execution", {}).get("idf_adapter_report")
    if isinstance(execution_report, dict) and execution_report:
        reports.append(execution_report)

    plan = layer5.get("phase_5_1_3_plan", {})
    for result in plan.get("simulation_results", []) or []:
        report = result.get("idf_adapter_report")
        if isinstance(report, dict) and report:
            reports.append(report)

    return reports


def build_idf_adapter_summary_from_demo(demo_result: dict) -> dict:
    reports = collect_idf_adapter_reports(demo_result)
    if not reports:
        report = demo_result.get("idf_adapter_summary", {}) or {}
        reports = [report] if report else []

    metadata_only_actions = []
    warnings = []
    change_log = []
    for report in reports:
        metadata_only_actions.extend(report.get("actions_metadata_only", []) or [])
        warnings.extend(report.get("warnings", []) or [])
        change_log.extend(report.get("change_log", []) or [])

    return {
        "lighting_applied": any(report.get("lighting_applied", False) for report in reports),
        "hvac_setpoint_applied": any(report.get("hvac_setpoint_applied", False) for report in reports),
        "ventilation_applied": any(report.get("ventilation_applied", False) for report in reports),
        "metadata_only_actions": dedupe_dicts(metadata_only_actions),
        "warnings": dedupe_strings(warnings),
        "change_log": change_log,
        "adapter_change_count": len(change_log),
    }


def build_phase57_dashboard_summary(demo_result: dict, artifacts_exported: bool = False) -> dict:
    layer5 = demo_result.get("layer5_result", {})
    dashboard = layer5.get("phase_5_6_dashboard", {})
    execution = layer5.get("phase_5_4_execution", {})
    learning = layer5.get("phase_5_5_learning", {})
    adapter = build_idf_adapter_summary_from_demo(demo_result)
    selected_provider = demo_result.get("selected_provider", "")
    digital_twin_execution = bool(demo_result.get("digital_twin_execution", False))
    judge_ready = (
        selected_provider in {"ollama", "openrouter"}
        and execution.get("execution_status") == "executed"
        and dashboard.get("safetyGovernorUsed") is True
        and dashboard.get("rlBanditUsed") is True
        and dashboard.get("knowledgeGraphUsed") is True
        and digital_twin_execution is True
        and demo_result.get("real_building_execution") is False
        and artifacts_exported
    )
    return {
        "layer": "Layer 5",
        "phase": "5.7",
        "realLLMFullLoopEnabled": True,
        "selectedProvider": selected_provider,
        "ollamaUsed": selected_provider == "ollama",
        "openRouterUsed": selected_provider == "openrouter",
        "mockUsed": selected_provider == "mock",
        "energyPlusUsed": True,
        "digitalTwinExecution": digital_twin_execution,
        "realBuildingExecution": False,
        "lightingAppliedInIDF": adapter["lighting_applied"],
        "hvacSetpointAppliedInIDF": adapter["hvac_setpoint_applied"],
        "ventilationAppliedInIDF": adapter["ventilation_applied"],
        "metadataOnlyActions": adapter["metadata_only_actions"],
        "adapterWarnings": adapter["warnings"],
        "adapterChangeCount": adapter["adapter_change_count"],
        "candidateBundlesGenerated": demo_result.get("candidate_count", 0),
        "candidateBundlesSimulated": layer5.get("phase_5_1_3_plan", {}).get("simulation_count", 0),
        "safetyGovernorUsed": bool(dashboard.get("safetyGovernorUsed", True)),
        "rlBanditUsed": bool(dashboard.get("rlBanditUsed", True)),
        "knowledgeGraphUsed": bool(dashboard.get("knowledgeGraphUsed", True)),
        "memoryUpdated": bool(learning.get("memory_updated", False)),
        "banditUpdated": bool(learning.get("bandit_updated", False)),
        "knowledgeGraphUpdated": bool(learning.get("knowledge_graph_updated", False)),
        "energySavedPercent": execution.get("energy_saved_percent", 0),
        "carbonReducedPercent": execution.get("carbon_reduced_percent", 0),
        "comfortStatus": execution.get("comfort_status", "Unknown"),
        "judgeReady": judge_ready,
    }


def build_phase57_markdown(demo_result: dict, dashboard: dict) -> str:
    adapter = demo_result.get("idf_adapter_summary", {})
    return "\n".join(
        [
            "# ForgeHive Layer 5 Phase 5.7 Real LLM Full Loop",
            "",
            "## Provider",
            f"- Selected provider: {demo_result.get('selected_provider')}",
            f"- Model: {demo_result.get('model')}",
            f"- Fallback used: {demo_result.get('fallback_used')}",
            "",
            "## Candidate Bundles",
            f"- Generated: {demo_result.get('candidate_count', 0)}",
            "",
            "## IDF Adapter",
            f"- Lighting applied: {adapter.get('lighting_applied')}",
            f"- HVAC setpoint applied: {adapter.get('hvac_setpoint_applied')}",
            f"- Ventilation applied: {adapter.get('ventilation_applied')}",
            f"- Metadata-only actions: {len(adapter.get('metadata_only_actions', []))}",
            f"- Warnings: {len(adapter.get('warnings', []))}",
            "",
            "## Digital Twin Result",
            f"- Digital twin execution: {demo_result.get('digital_twin_execution')}",
            f"- Real building execution: {demo_result.get('real_building_execution')}",
            f"- Energy saved: {demo_result.get('energy_saved_percent', 0)}%",
            f"- Carbon reduced: {demo_result.get('carbon_reduced_percent', 0)}%",
            f"- Comfort status: {demo_result.get('comfort_status', 'Unknown')}",
            "",
            "## Learning",
            f"- Bandit updated: {demo_result.get('bandit_updated')}",
            f"- Memory updated: {demo_result.get('memory_updated')}",
            f"- Knowledge Graph updated: {demo_result.get('knowledge_graph_updated')}",
            "",
            "## Judge Readiness",
            f"- Judge ready: {dashboard.get('judgeReady')}",
            demo_result.get("judge_summary", ""),
            "",
            "No real building was controlled. All execution was limited to the EnergyPlus digital twin.",
            "",
        ]
    )


def export_phase57_artifacts(demo_result: dict) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    adapter_summary = build_idf_adapter_summary_from_demo(demo_result)
    enriched = dict(demo_result)
    enriched["idf_adapter_summary"] = adapter_summary

    full_loop_file = OUTPUT_DIR / "layer5_7_real_ollama_full_loop.json"
    adapter_file = OUTPUT_DIR / "layer5_7_idf_adapter_report.json"
    dashboard_file = OUTPUT_DIR / "layer5_7_dashboard_summary.json"
    summary_file = OUTPUT_DIR / "layer5_7_summary.md"

    full_loop_file.write_text(json.dumps(enriched, indent=2))
    adapter_file.write_text(json.dumps(adapter_summary, indent=2))
    provisional_dashboard = build_phase57_dashboard_summary(enriched, artifacts_exported=True)
    dashboard_file.write_text(json.dumps(provisional_dashboard, indent=2))
    summary_file.write_text(build_phase57_markdown(enriched, provisional_dashboard))

    return {
        "output_dir": str(OUTPUT_DIR),
        "generated_files": {
            "real_ollama_full_loop": str(full_loop_file),
            "idf_adapter_report": str(adapter_file),
            "dashboard_summary": str(dashboard_file),
            "markdown_summary": str(summary_file),
        },
        "dashboard_summary": provisional_dashboard,
    }
