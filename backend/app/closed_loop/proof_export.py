import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "layer_5_closed_loop"


def build_markdown_summary(plan: dict, dashboard: dict) -> str:
    selected = plan.get("selected_bundle") or {}
    return "\n".join(
        [
            "# ForgeHive Layer 5 Phase 5.1-5.3 Closed Loop",
            "",
            "## Phase 5.1: Simulation",
            f"Layer 5 simulated {plan.get('simulation_count', 0)} candidate bundle(s) in the EnergyPlus digital twin path. Failed simulations are captured and do not stop the batch.",
            "",
            "## Phase 5.2: Reward Ranking",
            "ForgeHive ranked bundles using simulated energy/carbon impact, comfort and anomaly penalties, a read-only Layer 3 bandit prior, and Layer 4 Knowledge Graph relevance.",
            "",
            "## Phase 5.3: Final Safety Gate",
            "The selected bundle was converted into Layer 3 ControlAction objects and checked with the existing Safety Governor.",
            "",
            "## Selected Bundle",
            f"- Name: {selected.get('bundle_name', 'none')}",
            f"- Score: {selected.get('total_score', 0)}",
            f"- Execution ready: {dashboard.get('executionReady')}",
            f"- Risk level: {dashboard.get('riskLevel')}",
            "",
            "## Why Execution Is Not Applied Yet",
            "Phase 5.1-5.3 produces an execution-ready plan only. It does not apply controls, write to a real building, or update learning as if execution happened.",
            "",
            "## Phase 5.4 Next Step",
            "Phase 5.4 will apply approved actions inside the EnergyPlus digital twin and produce execution feedback.",
            "",
        ]
    )


def export_layer5_phase_1_3_proof(plan: dict) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    proof_file = OUTPUT_DIR / "layer5_phase_1_3_proof.json"
    dashboard_file = OUTPUT_DIR / "layer5_dashboard_summary.json"
    summary_file = OUTPUT_DIR / "layer5_summary.md"

    dashboard = plan.get("dashboard_summary", {})
    proof_file.write_text(json.dumps(plan, indent=2))
    dashboard_file.write_text(json.dumps(dashboard, indent=2))
    summary_file.write_text(build_markdown_summary(plan, dashboard))

    return {
        "output_dir": str(OUTPUT_DIR),
        "generated_files": {
            "proof": str(proof_file),
            "dashboard_summary": str(dashboard_file),
            "markdown_summary": str(summary_file),
        },
        "dashboard_summary": dashboard,
    }


def build_full_closed_loop_markdown(
    plan_5_1_3: dict,
    execution_result: dict,
    learning_report: dict,
    dashboard: dict,
) -> str:
    selected = plan_5_1_3.get("selected_bundle") or {}
    approval = plan_5_1_3.get("final_safety_approval") or {}
    comparison = learning_report.get("expected_vs_actual", {})
    adapter = execution_result.get("idf_adapter_report", {})
    return "\n".join(
        [
            "# ForgeHive Layer 5 Phase 5.4-5.6 Full Closed Loop",
            "",
            "## Natural Language Request",
            plan_5_1_3.get("user_message", ""),
            "",
            "## Candidate Bundles",
            f"- Generated: {plan_5_1_3.get('candidate_count', 0)}",
            f"- Simulations run: {plan_5_1_3.get('simulation_count', 0)}",
            f"- Successful simulations: {plan_5_1_3.get('successful_simulation_count', 0)}",
            "",
            "## Selected Bundle",
            f"- Name: {selected.get('bundle_name', 'none')}",
            f"- Score: {selected.get('total_score', 0)}",
            "",
            "## Safety Approval",
            f"- Execution ready: {approval.get('execution_ready', False)}",
            f"- Risk level: {approval.get('risk_level', '')}",
            f"- Summary: {approval.get('safety_summary', '')}",
            "",
            "## Digital Twin Execution Result",
            f"- Status: {execution_result.get('execution_status')}",
            f"- Scope: {execution_result.get('execution_scope')}",
            f"- Run dir: {execution_result.get('run_dir')}",
            f"- Lighting applied in IDF: {adapter.get('lighting_applied', False)}",
            f"- HVAC setpoint applied in IDF: {adapter.get('hvac_setpoint_applied', False)}",
            f"- Ventilation applied in IDF: {adapter.get('ventilation_applied', False)}",
            f"- Metadata-only actions: {len(adapter.get('actions_metadata_only', []))}",
            "",
            "## Energy / Carbon / Comfort Impact",
            f"- Energy saved: {execution_result.get('energy_saved_percent', 0)}%",
            f"- Carbon reduced: {execution_result.get('carbon_reduced_percent', 0)}%",
            f"- Comfort status: {execution_result.get('comfort_status', 'Unknown')}",
            f"- Anomaly count: {execution_result.get('anomaly_count', 0)}",
            "",
            "## Learning Update",
            f"- Learning status: {learning_report.get('learning_status')}",
            f"- Actual reward: {learning_report.get('actual_reward')}",
            f"- Bandit updated: {learning_report.get('bandit_updated')}",
            f"- Memory updated: {learning_report.get('memory_updated')}",
            f"- Knowledge Graph updated: {learning_report.get('knowledge_graph_updated')}",
            f"- Energy delta vs expected: {comparison.get('delta_energy_saving', 0)} percentage points",
            f"- Carbon delta vs expected: {comparison.get('delta_carbon_reduction', 0)} percentage points",
            "",
            "## Self-Correction Recommendation",
            learning_report.get("self_correction", {}).get("summary", ""),
            "",
            "## Safety Boundary",
            "No real building execution occurred. Phase 5.4 execution is limited to the EnergyPlus digital twin only.",
            "",
            "## Judge Summary",
            dashboard.get("judgeSummary", ""),
            "",
        ]
    )


def export_layer5_full_closed_loop_proof(
    plan_5_1_3: dict,
    execution_result: dict,
    learning_report: dict,
    dashboard: dict,
) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    proof_file = OUTPUT_DIR / "layer5_full_closed_loop_proof.json"
    execution_file = OUTPUT_DIR / "layer5_execution_result.json"
    learning_file = OUTPUT_DIR / "layer5_learning_report.json"
    dashboard_file = OUTPUT_DIR / "layer5_dashboard_final.json"
    summary_file = OUTPUT_DIR / "layer5_final_summary.md"

    proof = {
        "project": {"name": "ForgeHive", "layer": "Layer 5", "phase": "5.4-5.6"},
        "phase_5_1_3_plan": plan_5_1_3,
        "phase_5_4_execution": execution_result,
        "phase_5_5_learning": learning_report,
        "phase_5_6_dashboard": dashboard,
        "real_building_execution": False,
    }

    proof_file.write_text(json.dumps(proof, indent=2))
    execution_file.write_text(json.dumps(execution_result, indent=2))
    learning_file.write_text(json.dumps(learning_report, indent=2))
    dashboard_file.write_text(json.dumps(dashboard, indent=2))
    summary_file.write_text(build_full_closed_loop_markdown(plan_5_1_3, execution_result, learning_report, dashboard))

    return {
        "output_dir": str(OUTPUT_DIR),
        "generated_files": {
            "full_proof": str(proof_file),
            "execution_result": str(execution_file),
            "learning_report": str(learning_file),
            "dashboard_final": str(dashboard_file),
            "markdown_summary": str(summary_file),
        },
        "dashboard": dashboard,
    }
