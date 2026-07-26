import json
from datetime import datetime

from backend.app.energyplus.comparator import compare_runs
from backend.app.energyplus.config import DEFAULT_MODEL, RUNS_DIR
from backend.app.energyplus.parser import parse_energyplus_run
from backend.app.energyplus.runner import run_energyplus
from backend.app.energyplus.strategy_applier import apply_eco_strategy


if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_dir = RUNS_DIR / f"phase_1_5_eco_mode_{timestamp}"
    modified_model = scenario_dir / "modified_model.idf"
    comparison_file = scenario_dir / "comparison.json"

    scenario_dir.mkdir(parents=True, exist_ok=True)

    strategy_info = apply_eco_strategy(DEFAULT_MODEL, modified_model)

    optimized_run = run_energyplus(
        run_name="phase_1_5_eco_mode",
        model_path=modified_model,
        clean=False,
    )

    baseline_result = parse_energyplus_run(RUNS_DIR / "baseline")
    optimized_result = parse_energyplus_run(optimized_run["output_dir"])

    comparison = compare_runs(baseline_result, optimized_result, strategy_info)

    comparison_file.write_text(json.dumps(comparison, indent=2))

    print(json.dumps(comparison, indent=2))

    passed = (
        baseline_result["simulation"]["completed"]
        and optimized_result["simulation"]["completed"]
        and baseline_result["metrics"]["available"]
        and optimized_result["metrics"]["available"]
        and comparison_file.exists()
    )

    if passed:
        print("\nPhase 1.5 test passed: Baseline vs optimized comparison generated successfully.")
    else:
        print("\nPhase 1.5 test failed: Check baseline, optimized run, and comparison outputs.")
        raise SystemExit(1)
