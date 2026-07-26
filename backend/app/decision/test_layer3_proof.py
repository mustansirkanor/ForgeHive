import json
from pathlib import Path

from backend.app.decision.proof_export import (
    generate_layer3_proof_package,
    save_layer3_proof_artifacts,
)


if __name__ == "__main__":
    proof_package = generate_layer3_proof_package()

    print(json.dumps(proof_package["project"], indent=2))
    print(json.dumps(proof_package["status"], indent=2))
    print(json.dumps(proof_package["dashboard_summary"], indent=2))
    print(json.dumps(proof_package["judging_alignment"], indent=2))

    saved_paths = save_layer3_proof_artifacts()
    print(json.dumps(saved_paths, indent=2))

    safe_decision = proof_package["safety_proof"]["safe_action_test"]["decision"]
    unsafe_decision = proof_package["safety_proof"]["unsafe_action_test"]["decision"]
    saved_files_exist = all(Path(path).exists() for path in saved_paths.values())

    passed = (
        proof_package["project"]["name"] == "ForgeHive"
        and proof_package["project"]["layer"] == "Layer 3"
        and proof_package["status"]["layer_complete"] is True
        and proof_package["status"]["actions_executed"] is False
        and bool(proof_package.get("goal_decision_suite"))
        and bool(proof_package.get("multi_agent_proof"))
        and bool(proof_package.get("safety_proof"))
        and bool(proof_package.get("carbon_scheduler_proof"))
        and bool(proof_package.get("bandit_proof"))
        and bool(proof_package.get("dashboard_summary"))
        and len(proof_package.get("future_mcp_tool_preview", [])) >= 4
        and safe_decision.get("approved") is True
        and unsafe_decision.get("approved") is False
        and saved_files_exist
    )

    if passed:
        print("\nPhase 3.7 test passed: Layer 3 proof package and demo export are working.")
    else:
        print("\nPhase 3.7 test failed: Layer 3 proof package did not meet expected checks.")
        raise SystemExit(1)
