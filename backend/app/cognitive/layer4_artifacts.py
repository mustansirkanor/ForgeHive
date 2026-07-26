import json
from pathlib import Path

from backend.app.cognitive.demo_scenarios import run_layer4_demo_scenarios
from backend.app.cognitive.mcp_tool_registry import list_mcp_tools


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "layer_4_cognitive"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2))


def build_markdown_summary(demo_output: dict, dashboard_summary: dict) -> str:
    scenario_lines = [
        f"- {entry['scenario']['prompt']} -> {entry['intent'].get('intent')} ({entry.get('candidate_count', 0)} candidate bundles)"
        for entry in demo_output.get("outputs", [])
    ]
    return "\n".join(
        [
            "# ForgeHive Layer 4.6 Cognitive Operator",
            "",
            "## What Phase 4.6 Adds",
            "Phase 4.6 adds a natural language building operator that turns normal operator requests into detected intents, building context, knowledge graph matches, candidate action bundles, provider traces, and concise explanations.",
            "",
            "## Example Prompts",
            *scenario_lines,
            "",
            "## How ForgeHive Reasons",
            "ForgeHive classifies the user request, reads Layer 2 building intelligence through MCP-style tools, retrieves Knowledge Graph context, generates candidate bundles through the configured LLM provider chain, validates candidate bundles, and explains the trace.",
            "",
            "## Why Execution Is Blocked In Layer 4",
            "Layer 4 is reasoning-only. It does not execute actions, apply controls, run EnergyPlus, or bypass the Safety Governor. Candidate bundles are proposals for later simulation and approval.",
            "",
            "## What Layer 5 Does Next",
            "Layer 5.1-5.3 will simulate candidate bundles in EnergyPlus, rank plans using reward/RL-style scoring, and apply final Safety Governor approval. Phase 5.4 will execute only approved digital-twin actions, and later feedback phases will record outcomes to memory, the Knowledge Graph, and the bandit selector.",
            "",
            "## Dashboard Summary",
            f"- Status: {dashboard_summary.get('status')}",
            f"- Natural language operator enabled: {dashboard_summary.get('naturalLanguageOperatorEnabled')}",
            f"- Real LLM provider enabled: {dashboard_summary.get('realLLMProviderEnabled')}",
            f"- Execution enabled: {dashboard_summary.get('executionEnabled')}",
            f"- Ready for Layer 5: {dashboard_summary.get('readyForLayer5')}",
            "",
            "## Demo Value",
            "For Honeywell hackathon judges, Phase 4.6 makes ForgeHive easy to demo: type a building request, inspect the reasoning trace, show the candidate plans, and prove that safety boundaries are enforced before Layer 5 closed-loop approval.",
            "",
        ]
    )


def export_layer4_cognitive_artifacts() -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    demo_output = run_layer4_demo_scenarios()
    sample_output = demo_output.get("outputs", [{}])[0].get("operator_output", {})
    sample_trace = sample_output.get("llm_provider_trace", {})

    dashboard_summary = {
        "layer": "Layer 4",
        "phase": "Phase 4.6",
        "status": "complete",
        "naturalLanguageOperatorEnabled": True,
        "realLLMProviderEnabled": sample_trace.get("selected_provider") in {"ollama", "openrouter"},
        "providerFallbackEnabled": True,
        "executionEnabled": False,
        "reasoningOnly": True,
        "mcpToolsAvailable": len(list_mcp_tools()),
        "knowledgeGraphEnabled": True,
        "candidateBundleGenerationEnabled": True,
        "demoScenarioCount": demo_output.get("scenario_count", 0),
        "sampleIntent": sample_output.get("intent", {}).get("intent"),
        "sampleSelectedProvider": sample_trace.get("selected_provider"),
        "sampleCandidateCount": sample_output.get("candidate_count", 0),
        "readyForLayer5": True,
    }

    operator_demo_file = OUTPUT_DIR / "layer4_operator_demo.json"
    dashboard_file = OUTPUT_DIR / "layer4_dashboard_summary.json"
    summary_file = OUTPUT_DIR / "layer4_summary.md"

    write_json(operator_demo_file, demo_output)
    write_json(dashboard_file, dashboard_summary)
    summary_file.write_text(build_markdown_summary(demo_output, dashboard_summary))

    return {
        "output_dir": str(OUTPUT_DIR),
        "generated_files": {
            "operator_demo": str(operator_demo_file),
            "dashboard_summary": str(dashboard_file),
            "markdown_summary": str(summary_file),
        },
        "dashboard_summary": dashboard_summary,
    }
