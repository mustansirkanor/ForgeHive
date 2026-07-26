import hashlib
import json
from pathlib import Path

from backend.app.closed_loop.bundle_simulator import CACHE_FILE, simulate_action_bundle, simulate_candidate_bundles
from backend.app.energyplus.config import DEFAULT_MODEL


def deterministic_bundle() -> dict:
    return {
        "bundle_name": "test_empty_room_bundle",
        "goal": "reduce_energy_keep_comfort_safe",
        "event_type": "empty_room_detected",
        "actions": [
            {
                "action_type": "lighting_adjustment",
                "target": "unoccupied_zones",
                "description": "Dim lights for empty room.",
                "parameters": {"lighting_level_percent": 25},
                "source": "test",
                "confidence": 0.9,
            },
            {
                "action_type": "hvac_setpoint_adjustment",
                "target": "unoccupied_zones",
                "description": "Relax cooling setpoint safely.",
                "parameters": {"cooling_setpoint_c": 28},
                "source": "test",
                "confidence": 0.85,
            },
            {
                "action_type": "ventilation_adjustment",
                "target": "unoccupied_zones",
                "description": "Reduce ventilation within safe bounds.",
                "parameters": {"ventilation_percent": 40},
                "source": "test",
                "confidence": 0.8,
            },
        ],
        "rationale": "Test candidate for Layer 5 simulation.",
        "constraints": [],
        "expected_outcome": {},
        "created_by": "test",
        "requires_simulation": True,
        "fallback_used": False,
    }


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    before_hash = file_hash(DEFAULT_MODEL)
    result = simulate_action_bundle(deterministic_bundle())
    after_hash = file_hash(DEFAULT_MODEL)

    failed_bundle = dict(deterministic_bundle())
    failed_bundle["bundle_name"] = "failed_schema_bundle"
    failed_bundle["actions"] = [{"action_type": "unknown_action"}]
    batch = simulate_candidate_bundles([deterministic_bundle(), failed_bundle])

    print(json.dumps({"single_result": result, "batch_summary": {
        "simulation_count": batch.get("simulation_count"),
        "successful_simulation_count": batch.get("successful_simulation_count"),
        "failed_count": len(batch.get("failed_results", [])),
    }}, indent=2))

    assert result["simulation_status"] in {"success", "failed", "skipped"}
    assert "energy_kwh" in result
    assert "carbon_kg" in result
    assert result.get("run_dir") or result.get("error")
    assert before_hash == after_hash
    assert batch["simulation_count"] == 2
    assert CACHE_FILE.exists() or result["simulation_status"] == "failed"

    print("\nPhase 5.1 bundle simulator test passed.")
