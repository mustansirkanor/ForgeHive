import json
from pathlib import Path

from backend.app.intelligence.intelligence_api import (
    get_building_intelligence_package,
    get_dashboard_ready_intelligence,
    save_intelligence_package,
)


if __name__ == "__main__":
    package = get_building_intelligence_package()
    dashboard = get_dashboard_ready_intelligence()
    saved = save_intelligence_package()

    print(json.dumps(package, indent=2))
    print(json.dumps(dashboard, indent=2))
    print(json.dumps(saved, indent=2))

    generated_files = saved["generated_files"]
    files_exist = all(Path(path).exists() for path in generated_files.values())

    passed = (
        "building_state" in package
        and "comfort" in package
        and "score" in package
        and "anomalies" in package
        and "memory_summary" in package
        and package["validation"]["valid"] is True
        and 0 <= package["score"]["overall"] <= 100
        and "overallScore" in dashboard
        and files_exist
    )

    if passed:
        print("\nPhase 2.7 test passed: Unified building intelligence API is working.")
    else:
        print("\nPhase 2.7 test failed: Unified building intelligence API did not meet expected checks.")
        raise SystemExit(1)
