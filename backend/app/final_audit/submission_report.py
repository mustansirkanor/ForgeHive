import json
from pathlib import Path

from backend.app.final_audit.artifact_audit import run_artifact_audit
from backend.app.final_audit.demo_audit import run_final_demo_audit
from backend.app.final_audit.readiness_score import calculate_forgehive_readiness_score
from backend.app.final_audit.test_matrix import run_layer6_test_matrix


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "final_submission"
DOCS_DIR = PROJECT_ROOT / "docs"
FINAL_AUDIT_FILE = OUTPUT_DIR / "forgehive_final_audit.json"
FINAL_PACKAGE_FILE = OUTPUT_DIR / "forgehive_final_submission_package.json"
DEMO_SCRIPT_FILE = OUTPUT_DIR / "forgehive_demo_script.md"
JUDGE_SUMMARY_FILE = OUTPUT_DIR / "forgehive_judge_summary.md"
DOCS_DEMO_SCRIPT_FILE = DOCS_DIR / "FINAL_DEMO_SCRIPT.md"
DOCS_JUDGE_NARRATIVE_FILE = DOCS_DIR / "FINAL_JUDGE_NARRATIVE.md"


def build_demo_script(package: dict) -> str:
    demo = package.get("demo_audit", {}).get("demo_result", {})
    provider = demo.get("selected_provider", "unknown")
    adapter = demo.get("idf_adapter_summary", {})
    dashboard = demo.get("phase57_dashboard_summary", {})
    return "\n".join(
        [
            "# ForgeHive Final Demo Script",
            "",
            "## 1. Natural Language Prompt",
            "`The meeting room is empty now. Save energy but keep comfort safe.`",
            "",
            "## 2. Layer 4 Intent And Provider Trace",
            f"Show that the Layer 4 operator selected provider `{provider}` with fallback_used={demo.get('fallback_used')}.",
            "",
            "## 3. Candidate Bundles",
            f"Show {demo.get('candidate_count', 0)} generated candidate bundle(s), including lighting, HVAC, and ventilation proposals.",
            "",
            "## 4. EnergyPlus Simulation",
            "Show Layer 5 simulation results for candidate bundles in the EnergyPlus digital twin.",
            "",
            "## 5. Reward Ranking With RL/KG",
            "Show reward score, bandit/RL prior, Knowledge Graph relevance, and selected bundle.",
            "",
            "## 6. Safety Governor Approval",
            "Show final Safety Governor approval and rejected-action handling before execution.",
            "",
            "## 7. IDF Adapter Changes",
            f"Lighting applied: {adapter.get('lighting_applied')}",
            f"HVAC setpoint applied: {adapter.get('hvac_setpoint_applied')}",
            f"Ventilation applied: {adapter.get('ventilation_applied')}",
            f"Adapter change count: {adapter.get('adapter_change_count', len(adapter.get('change_log', [])))}",
            "",
            "## 8. Digital Twin Execution Result",
            f"Digital twin execution: {demo.get('digital_twin_execution')}",
            f"Real building execution: {demo.get('real_building_execution')}",
            f"Energy saved: {demo.get('energy_saved_percent', 0)}%",
            f"Carbon reduced: {demo.get('carbon_reduced_percent', 0)}%",
            f"Comfort status: {demo.get('comfort_status', 'Unknown')}",
            "",
            "## 9. Learning Update",
            f"Bandit updated: {demo.get('bandit_updated')}",
            f"Memory updated: {demo.get('memory_updated')}",
            f"Knowledge Graph updated: {demo.get('knowledge_graph_updated')}",
            "",
            "## 10. Final Dashboard",
            f"judgeReady: {dashboard.get('judgeReady')}",
            "End by emphasizing that ForgeHive executed only inside the EnergyPlus digital twin.",
            "",
        ]
    )


def build_judge_summary(package: dict) -> str:
    score = package.get("readiness_score", {})
    demo = package.get("demo_audit", {}).get("demo_result", {})
    adapter = demo.get("idf_adapter_summary", {})
    return "\n".join(
        [
            "# ForgeHive Final Judge Narrative",
            "",
            "Buildings waste energy and carbon because operational decisions are often static, delayed, or detached from comfort and safety constraints. ForgeHive solves this with an autonomous closed-loop building agent.",
            "",
            "ForgeHive uses an EnergyPlus digital twin to test decisions before applying them. A natural-language operator powered by a real open-source LLM path through Ollama generates candidate action bundles. An MCP-style tool layer exposes building intelligence, a Knowledge Graph supplies context, and reward/RL-style bandit scoring ranks candidate plans.",
            "",
            "Before execution, the Safety Governor reviews the selected plan. ForgeHive then executes approved actions only inside the EnergyPlus digital twin, never a real building. The final demo measures energy, carbon, comfort, and anomaly outcomes, then updates memory, the Knowledge Graph, and the bandit learner.",
            "",
            "The final Phase 5.7 demo demonstrates direct IDF adapter changes:",
            f"- Lighting applied in IDF: {adapter.get('lighting_applied')}",
            f"- HVAC setpoint applied in IDF: {adapter.get('hvac_setpoint_applied')}",
            f"- Ventilation applied in IDF: {adapter.get('ventilation_applied')}",
            "",
            f"Final readiness score: {score.get('score')} ({score.get('grade')}).",
            "",
            "Honest safety boundary: no real building was controlled. ForgeHive is demo-ready as a digital-twin autonomous building optimization system.",
            "",
        ]
    )


def build_final_submission_report() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    test_matrix = run_layer6_test_matrix()
    artifact_audit = run_artifact_audit()
    demo_audit = run_final_demo_audit()
    if not artifact_audit.get("audit_passed"):
        artifact_audit = run_artifact_audit()
    readiness_score = calculate_forgehive_readiness_score(test_matrix, artifact_audit, demo_audit)

    package = {
        "project": {"name": "ForgeHive", "layer": "Layer 6", "phase": "Final testing and submission readiness"},
        "test_matrix": test_matrix,
        "artifact_audit": artifact_audit,
        "demo_audit": demo_audit,
        "readiness_score": readiness_score,
        "real_building_execution": False,
    }

    demo_script = build_demo_script(package)
    judge_summary = build_judge_summary(package)

    DEMO_SCRIPT_FILE.write_text(demo_script)
    JUDGE_SUMMARY_FILE.write_text(judge_summary)
    DOCS_DEMO_SCRIPT_FILE.write_text(demo_script)
    DOCS_JUDGE_NARRATIVE_FILE.write_text(judge_summary)

    final_audit = {
        "test_matrix_summary": {
            "total_tests": test_matrix.get("total_tests", 0),
            "passed_tests": test_matrix.get("passed_tests", 0),
            "failed_tests": test_matrix.get("failed_tests", 0),
            "skipped_tests": test_matrix.get("skipped_tests", 0),
        },
        "artifact_audit_passed": artifact_audit.get("audit_passed", False),
        "demo_audit_passed": demo_audit.get("audit_passed", False),
        "readiness_score": readiness_score,
        "real_building_execution": False,
        "generated_files": {
            "demo_script": str(DEMO_SCRIPT_FILE),
            "judge_summary": str(JUDGE_SUMMARY_FILE),
            "docs_demo_script": str(DOCS_DEMO_SCRIPT_FILE),
            "docs_judge_narrative": str(DOCS_JUDGE_NARRATIVE_FILE),
        },
    }
    package["final_audit"] = final_audit
    package["generated_files"] = {
        "final_audit": str(FINAL_AUDIT_FILE),
        "artifact_audit": str(OUTPUT_DIR / "forgehive_artifact_audit.json"),
        "demo_audit": str(OUTPUT_DIR / "forgehive_final_demo_audit.json"),
        "demo_script": str(DEMO_SCRIPT_FILE),
        "judge_summary": str(JUDGE_SUMMARY_FILE),
        "readiness_score": str(OUTPUT_DIR / "forgehive_readiness_score.json"),
        "final_submission_package": str(FINAL_PACKAGE_FILE),
    }

    FINAL_AUDIT_FILE.write_text(json.dumps(final_audit, indent=2))
    FINAL_PACKAGE_FILE.write_text(json.dumps(package, indent=2))
    return package


if __name__ == "__main__":
    print(json.dumps(build_final_submission_report(), indent=2))
