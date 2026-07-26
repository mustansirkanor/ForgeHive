from backend.app.energyplus.config import RUNS_DIR
from backend.app.energyplus.proof_package import (
    find_latest_comparison_file,
    load_comparison,
)


COMFORT_NOTE = (
    "Comfort violation minutes are placeholder values in Layer 1 and will be "
    "computed in Layer 2."
)


def round_metric(value) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def build_error_response(message: str) -> dict:
    return {
        "error": True,
        "message": message,
        "source": "latest_comparison_json",
    }


def load_latest_comparison_safely() -> dict:
    try:
        comparison_file = find_latest_comparison_file(RUNS_DIR)
        return load_comparison(comparison_file)
    except (FileNotFoundError, ValueError, OSError) as exc:
        return build_error_response(str(exc))


def build_comparison_response(comparison: dict, optimized_key: str) -> dict:
    if comparison.get("error"):
        return comparison

    baseline = comparison.get("baseline", {})
    optimized = comparison.get("optimized", {})
    savings = comparison.get("savings", {})

    return {
        "baseline": {
            "energy_kwh": round_metric(baseline.get("electricity_kwh")),
            "carbon_kg": round_metric(baseline.get("carbon_kg")),
            "comfort_violation_minutes": 0,
        },
        optimized_key: {
            "energy_kwh": round_metric(optimized.get("electricity_kwh")),
            "carbon_kg": round_metric(optimized.get("carbon_kg")),
            "comfort_violation_minutes": 0,
        },
        "impact": {
            "energy_saved_percent": round_metric(savings.get("electricity_percent")),
            "carbon_reduced_percent": round_metric(savings.get("carbon_percent")),
            "comfort_status": "Safe",
        },
        "metadata": {
            "strategy_name": comparison.get("strategy_name", ""),
            "verdict": comparison.get("verdict", ""),
            "baseline_run_dir": comparison.get("baseline_run_dir", ""),
            "optimized_run_dir": comparison.get("optimized_run_dir", ""),
            "source": "latest_comparison_json",
            "comfort_note": COMFORT_NOTE,
        },
    }


def get_baseline_vs_forgehive_comparison() -> dict:
    comparison = load_latest_comparison_safely()
    return build_comparison_response(comparison, optimized_key="forgehive")


def get_baseline_vs_aura_comparison() -> dict:
    comparison = load_latest_comparison_safely()
    return build_comparison_response(comparison, optimized_key="aura")
