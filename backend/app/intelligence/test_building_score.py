import copy
import json

from backend.app.intelligence.building_score import (
    calculate_building_intelligence_score,
    get_latest_building_score,
)
from backend.app.intelligence.comfort_engine import apply_comfort_engine
from backend.app.intelligence.state_extractor import extract_building_state_from_latest_run


def score_fields_are_valid(score: dict) -> bool:
    return (
        0 <= score["energy_efficiency"] <= 100
        and 0 <= score["comfort"] <= 100
        and 0 <= score["carbon_optimization"] <= 100
        and 0 <= score["equipment_health"] <= 100
        and 0 <= score["anomaly_risk"] <= 100
        and 0 <= score["overall"] <= 100
        and bool(score["grade"])
    )


def create_bad_state():
    state = extract_building_state_from_latest_run()
    state = copy.deepcopy(state)

    state.energy.electricity_kwh = 52000.0
    state.energy.hvac_kwh = 18000.0
    state.carbon.carbon_kg = 23400.0

    state.zones[0].temperature_c = 31.0
    state.zones[0].occupancy_count = 4
    state.zones[0].co2_ppm = 1300.0

    state.zones[1].occupancy_count = 0
    state.zones[1].lighting_level_percent = 95.0

    return apply_comfort_engine(state)


if __name__ == "__main__":
    latest_score = get_latest_building_score()
    bad_state = create_bad_state()
    bad_score = calculate_building_intelligence_score(bad_state)

    print(json.dumps(latest_score, indent=2))
    print(json.dumps({"artificial_bad_state_score": bad_score}, indent=2))

    passed = (
        score_fields_are_valid(latest_score)
        and score_fields_are_valid(bad_score)
        and bad_score["overall"] < latest_score["overall"]
    )

    if passed:
        print("\nPhase 2.4 test passed: Building Intelligence Score is working.")
    else:
        print("\nPhase 2.4 test failed: Building Intelligence Score did not meet expected checks.")
        raise SystemExit(1)
