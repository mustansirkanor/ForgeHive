import json

from backend.app.energyplus.runner import run_energyplus


if __name__ == "__main__":
    result = run_energyplus(run_name="phase_1_3_test")

    print(json.dumps(result, indent=2))

    if result["completed"] and not result["has_fatal"] and not result["has_severe"]:
        print("\n? Phase 1.3 test passed: Python successfully ran EnergyPlus.")
    else:
        print("\n? Phase 1.3 test failed: Check eplusout.err and eplusout.end.")
