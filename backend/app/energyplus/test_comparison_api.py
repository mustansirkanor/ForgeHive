import json

from backend.app.energyplus.comparison_api import (
    get_baseline_vs_aura_comparison,
    get_baseline_vs_forgehive_comparison,
)


if __name__ == "__main__":
    forgehive_result = get_baseline_vs_forgehive_comparison()
    print(json.dumps(forgehive_result, indent=2))

    aura_result = get_baseline_vs_aura_comparison()

    passed = (
        "baseline" in forgehive_result
        and "forgehive" in forgehive_result
        and "impact" in forgehive_result
        and forgehive_result["baseline"]["energy_kwh"] > 0
        and forgehive_result["forgehive"]["energy_kwh"] > 0
        and forgehive_result["impact"]["comfort_status"] == "Safe"
        and "aura" in aura_result
    )

    if passed:
        print("\nPhase 1.7 test passed: Baseline vs ForgeHive comparison API is working.")
    else:
        print("\nPhase 1.7 test failed: Comparison API response is incomplete.")
        raise SystemExit(1)
