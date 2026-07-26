def calculate_percentage_change(baseline_value, optimized_value) -> float:
    baseline = float(baseline_value or 0)
    optimized = float(optimized_value or 0)

    if baseline == 0:
        return 0.0

    return ((baseline - optimized) / baseline) * 100


def compare_runs(baseline_result: dict, optimized_result: dict, strategy_info: dict) -> dict:
    baseline_electricity = baseline_result["metrics"]["electricity_kwh"]
    optimized_electricity = optimized_result["metrics"]["electricity_kwh"]
    baseline_carbon = baseline_result["metrics"]["carbon_kg"]
    optimized_carbon = optimized_result["metrics"]["carbon_kg"]

    electricity_savings = baseline_electricity - optimized_electricity
    carbon_savings = baseline_carbon - optimized_carbon

    if optimized_electricity < baseline_electricity:
        verdict = "Optimization reduced energy consumption."
    elif optimized_electricity == baseline_electricity:
        verdict = "No energy change detected."
    else:
        verdict = "Optimization increased energy consumption; strategy needs review."

    return {
        "baseline_run_dir": baseline_result["run_dir"],
        "optimized_run_dir": optimized_result["run_dir"],
        "strategy_name": strategy_info["strategy_name"],
        "strategy_changes": strategy_info["changes_applied"],
        "strategy_warnings": strategy_info["warnings"],
        "baseline": {
            "electricity_kwh": baseline_electricity,
            "carbon_kg": baseline_carbon,
        },
        "optimized": {
            "electricity_kwh": optimized_electricity,
            "carbon_kg": optimized_carbon,
        },
        "savings": {
            "electricity_kwh": electricity_savings,
            "electricity_percent": calculate_percentage_change(baseline_electricity, optimized_electricity),
            "carbon_kg": carbon_savings,
            "carbon_percent": calculate_percentage_change(baseline_carbon, optimized_carbon),
        },
        "verdict": verdict,
    }
