import json

from backend.app.intelligence.comfort_engine import (
    apply_comfort_engine,
    comfort_summary_dict,
    evaluate_zone_comfort,
)
from backend.app.intelligence.schemas import ZoneState, to_json, validate_building_state
from backend.app.intelligence.state_extractor import extract_building_state_from_latest_run


def create_test_zone(
    zone_id: str,
    temperature_c: float,
    occupancy_count: int,
    co2_ppm: float,
) -> ZoneState:
    return ZoneState(
        zone_id=zone_id,
        temperature_c=temperature_c,
        humidity_percent=50.0,
        occupancy_count=occupancy_count,
        co2_ppm=co2_ppm,
        lighting_level_percent=75.0,
        comfort_status="Unknown",
        source="explicit_comfort_engine_test",
    )


if __name__ == "__main__":
    state = extract_building_state_from_latest_run()
    state = apply_comfort_engine(state)
    validation = validate_building_state(state)

    safe_zone_result = evaluate_zone_comfort(
        create_test_zone("SAFE_TEST_ZONE", 23.5, 3, 700.0)
    )
    unsafe_zone_result = evaluate_zone_comfort(
        create_test_zone("UNSAFE_TEST_ZONE", 30.0, 3, 1200.0)
    )

    print(to_json(state))
    print(json.dumps(comfort_summary_dict(state), indent=2))
    print(json.dumps(validation, indent=2))
    print(json.dumps({"safe_zone_test": safe_zone_result}, indent=2))
    print(json.dumps({"unsafe_zone_test": unsafe_zone_result}, indent=2))

    passed = (
        validation["valid"]
        and state.comfort.source == "phase_2_3_comfort_engine"
        and 0 <= state.comfort.comfort_score <= 100
        and state.comfort.status in ["Safe", "Warning", "Unsafe"]
        and safe_zone_result["status"] == "comfortable"
        and unsafe_zone_result["status"] in ["violation", "warning"]
        and unsafe_zone_result["comfort_violation_minutes"] > 0
        and len(unsafe_zone_result["violations"]) > 0
    )

    if passed:
        print("\nPhase 2.3 test passed: Thermal comfort engine is working.")
    else:
        print("\nPhase 2.3 test failed: Thermal comfort engine did not meet expected checks.")
        raise SystemExit(1)
