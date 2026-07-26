import json

from backend.app.intelligence.schemas import to_json, validate_building_state
from backend.app.intelligence.state_extractor import extract_building_state_from_latest_run


def zones_have_valid_sources(state) -> bool:
    return all(zone.source == "derived_or_demo_placeholder" or bool(zone.source) for zone in state.zones)


if __name__ == "__main__":
    state = extract_building_state_from_latest_run()
    validation = validate_building_state(state)

    print(to_json(state))
    print(json.dumps(validation, indent=2))

    passed = (
        validation["valid"]
        and state.energy.electricity_kwh > 0
        and state.carbon.carbon_kg > 0
        and len(state.zones) >= 5
        and zones_have_valid_sources(state)
        and state.building_id == "forgehive_demo_building"
    )

    if passed:
        print("\nPhase 2.2 test passed: EnergyPlus outputs were converted into BuildingState.")
    else:
        print("\nPhase 2.2 test failed: EnergyPlus outputs could not be converted into a valid BuildingState.")
        raise SystemExit(1)
