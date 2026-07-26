import json

from backend.app.intelligence.schemas import (
    create_demo_building_state,
    to_dict,
    to_json,
    validate_building_state,
)


if __name__ == "__main__":
    state = create_demo_building_state()
    validation = validate_building_state(state)
    state_dict = to_dict(state)
    state_json = to_json(state)

    print(state_json)
    print(json.dumps(validation, indent=2))

    if validation["valid"] and isinstance(state_dict, dict) and state_json:
        print("\nPhase 2.1 test passed: Building state schema is valid and JSON serializable.")
    else:
        print("\nPhase 2.1 test failed: Building state schema is invalid.")
        raise SystemExit(1)
