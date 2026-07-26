import json
from pathlib import Path

from backend.app.energyplus.config import RUNS_DIR
from backend.app.energyplus.parser import parse_energyplus_run


def find_latest_completed_run(runs_dir: Path) -> Path | None:
    if not runs_dir.exists():
        return None

    run_dirs = [
        path
        for path in runs_dir.iterdir()
        if path.is_dir() and (path / "eplusout.end").exists()
    ]

    if not run_dirs:
        return None

    return max(run_dirs, key=lambda path: path.stat().st_mtime)


if __name__ == "__main__":
    latest_run = find_latest_completed_run(RUNS_DIR)

    if latest_run is None:
        print(json.dumps({"error": f"No EnergyPlus run folders found in {RUNS_DIR}"}, indent=2))
        print("\nPhase 1.4 test failed: No parseable EnergyPlus run folder was found.")
        raise SystemExit(1)

    result = parse_energyplus_run(latest_run)
    print(json.dumps(result, indent=2))

    if result["simulation"]["completed"] and result["metrics"]["available"]:
        print("\nPhase 1.4 test passed: EnergyPlus results parsed successfully.")
    else:
        print("\nPhase 1.4 test failed: Check EnergyPlus output files and parser messages.")
        raise SystemExit(1)
