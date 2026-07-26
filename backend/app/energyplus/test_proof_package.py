import json
from pathlib import Path

from backend.app.energyplus.proof_package import generate_layer1_proof_package


if __name__ == "__main__":
    result = generate_layer1_proof_package()
    print(json.dumps(result, indent=2))

    output_dir = Path(result["output_dir"])
    expected_files = [
        output_dir / "layer1_proof.json",
        output_dir / "dashboard_metrics.json",
        output_dir / "layer1_summary.md",
    ]

    if all(path.exists() for path in expected_files):
        print("\nPhase 1.6 test passed: Layer 1 proof package generated successfully.")
    else:
        print("\nPhase 1.6 test failed: One or more proof package files are missing.")
        raise SystemExit(1)
