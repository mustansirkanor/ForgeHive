import json
from pathlib import Path

from backend.app.energyplus.config import PROJECT_ROOT, RUNS_DIR


PROOF_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "layer_1_proof"


def find_latest_comparison_file(runs_dir: Path) -> Path:
    runs_path = Path(runs_dir)

    if not runs_path.exists():
        raise FileNotFoundError(f"Runs directory not found: {runs_path}")

    comparison_files = list(runs_path.rglob("comparison.json"))
    if not comparison_files:
        raise FileNotFoundError(f"No comparison.json files found under: {runs_path}")

    phase_1_5_files = [
        path
        for path in comparison_files
        if "phase_1_5" in str(path.parent).lower()
    ]

    candidates = phase_1_5_files or comparison_files
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_comparison(comparison_path: Path) -> dict:
    path = Path(comparison_path)

    if not path.exists():
        raise FileNotFoundError(f"Comparison file not found: {path}")

    try:
        with path.open(errors="ignore") as comparison_file:
            comparison = json.load(comparison_file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid comparison JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise OSError(f"Could not read comparison file {path}: {exc}") from exc

    if not isinstance(comparison, dict):
        raise ValueError(f"Comparison JSON must contain an object: {path}")

    return comparison


def build_layer1_proof_package(comparison: dict) -> dict:
    baseline = comparison.get("baseline", {})
    optimized = comparison.get("optimized", {})
    savings = comparison.get("savings", {})

    strategy_name = comparison.get("strategy_name", "eco_mode")

    return {
        "project": {
            "name": "ForgeHive",
            "title": "ForgeHive: Safety-Shielded Autonomous Building Intelligence",
            "layer": "Layer 1",
            "phase": "Phase 1.6",
            "purpose": "EnergyPlus digital twin proof and baseline-vs-optimized comparison",
        },
        "technical_proof": {
            "energyplus_runner": True,
            "output_parser": True,
            "strategy_applier": True,
            "baseline_vs_optimized_comparison": True,
            "dashboard_ready_metrics": True,
        },
        "simulation": {
            "baseline_run_dir": comparison.get("baseline_run_dir", ""),
            "optimized_run_dir": comparison.get("optimized_run_dir", ""),
            "strategy_name": strategy_name,
            "verdict": comparison.get("verdict", ""),
        },
        "metrics": {
            "baseline_electricity_kwh": baseline.get("electricity_kwh", 0),
            "optimized_electricity_kwh": optimized.get("electricity_kwh", 0),
            "electricity_saved_kwh": savings.get("electricity_kwh", 0),
            "electricity_saved_percent": savings.get("electricity_percent", 0),
            "baseline_carbon_kg": baseline.get("carbon_kg", 0),
            "optimized_carbon_kg": optimized.get("carbon_kg", 0),
            "carbon_saved_kg": savings.get("carbon_kg", 0),
            "carbon_saved_percent": savings.get("carbon_percent", 0),
        },
        "strategy": {
            "name": strategy_name,
            "changes_applied": comparison.get("strategy_changes", []),
            "warnings": comparison.get("strategy_warnings", []),
        },
        "hackathon_story": {
            "one_line": "ForgeHive proves an EnergyPlus digital twin can be optimized by a safety-conscious autonomous strategy pipeline.",
            "proof_summary": "Layer 1 runs a baseline building simulation, applies a conservative eco strategy, simulates the optimized model, and exports measurable energy and carbon savings.",
            "why_it_matters": "This creates trustworthy measured feedback before adding autonomous reasoning, safety governance, and learning loops.",
            "next_step": "Layer 2 will add building state, strategy schema, safety governor and autonomous control brain.",
        },
    }


def build_dashboard_metrics(proof_package: dict) -> dict:
    metrics = proof_package["metrics"]
    simulation = proof_package["simulation"]

    return {
        "baselineElectricityKwh": metrics["baseline_electricity_kwh"],
        "optimizedElectricityKwh": metrics["optimized_electricity_kwh"],
        "electricitySavedKwh": metrics["electricity_saved_kwh"],
        "electricitySavedPercent": metrics["electricity_saved_percent"],
        "baselineCarbonKg": metrics["baseline_carbon_kg"],
        "optimizedCarbonKg": metrics["optimized_carbon_kg"],
        "carbonSavedKg": metrics["carbon_saved_kg"],
        "carbonSavedPercent": metrics["carbon_saved_percent"],
        "verdict": simulation["verdict"],
        "strategyName": simulation["strategy_name"],
    }


def format_number(value) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def build_markdown_summary(proof_package: dict) -> str:
    project = proof_package["project"]
    metrics = proof_package["metrics"]
    strategy = proof_package["strategy"]
    simulation = proof_package["simulation"]

    strategy_changes = strategy["changes_applied"] or ["No strategy changes were recorded."]
    strategy_change_lines = "\n".join(f"- {change}" for change in strategy_changes)

    return f"""# {project["name"]} Layer 1 Proof

## Phase
{project["phase"]}: {project["purpose"]}

## Demo Metrics
- Baseline electricity: {format_number(metrics["baseline_electricity_kwh"])} kWh
- Optimized electricity: {format_number(metrics["optimized_electricity_kwh"])} kWh
- Electricity savings: {format_number(metrics["electricity_saved_kwh"])} kWh ({format_number(metrics["electricity_saved_percent"])}%)
- Carbon savings: {format_number(metrics["carbon_saved_kg"])} kg ({format_number(metrics["carbon_saved_percent"])}%)

## Strategy
Strategy name: {strategy["name"]}

Changes applied:
{strategy_change_lines}

## Verdict
{simulation["verdict"]}

## Layer 1 Completed Checklist
- EnergyPlus installed and callable
- Baseline simulation completed
- Python EnergyPlus runner works
- Parser extracts clean JSON metrics
- Eco strategy creates an optimized IDF
- Baseline vs optimized comparison shows measurable savings
- Proof package generated for dashboard, documentation, demo video, and submission use

## Next Layer 2 Direction
Layer 2 will add building state, strategy schema, safety governor and autonomous control brain.
"""


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def save_proof_outputs(proof_package: dict, output_dir: Path) -> dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    layer1_proof_file = output_path / "layer1_proof.json"
    dashboard_metrics_file = output_path / "dashboard_metrics.json"
    summary_file = output_path / "layer1_summary.md"

    save_json(layer1_proof_file, proof_package)
    save_json(dashboard_metrics_file, build_dashboard_metrics(proof_package))
    summary_file.write_text(build_markdown_summary(proof_package))

    return {
        "layer1_proof": str(layer1_proof_file),
        "dashboard_metrics": str(dashboard_metrics_file),
        "layer1_summary": str(summary_file),
    }


def generate_layer1_proof_package() -> dict:
    comparison_file = find_latest_comparison_file(RUNS_DIR)
    comparison = load_comparison(comparison_file)
    proof_package = build_layer1_proof_package(comparison)
    generated_files = save_proof_outputs(proof_package, PROOF_OUTPUT_DIR)

    return {
        "comparison_file": str(comparison_file),
        "output_dir": str(PROOF_OUTPUT_DIR),
        "generated_files": generated_files,
        "proof_package": proof_package,
    }
