import uuid

from backend.app.decision.action_schema import (
    ControlAction,
    create_demo_safe_action,
    create_demo_unsafe_action,
    to_json,
)
from backend.app.decision.safety_governor import check_action_safety, get_current_intelligence


if __name__ == "__main__":
    intelligence = get_current_intelligence()

    safe_action = create_demo_safe_action()
    safe_decision = check_action_safety(safe_action, intelligence)
    print(to_json(safe_action))
    print(to_json(safe_decision))

    unsafe_action = create_demo_unsafe_action()
    unsafe_decision = check_action_safety(unsafe_action, intelligence)
    print(to_json(unsafe_action))
    print(to_json(unsafe_decision))

    ventilation_action = ControlAction(
        action_id=str(uuid.uuid4()),
        strategy_name="ventilation_cutback",
        action_type="ventilation_adjustment",
        target="occupied_zones",
        description="Reduce ventilation in occupied zones to save fan energy.",
        parameters={
            "ventilation_percent": 20,
        },
        expected_energy_saved_percent=6.0,
        expected_carbon_reduced_percent=6.0,
        expected_comfort_impact="negative",
        source_agent="energy_agent",
        priority="medium",
    )
    ventilation_decision = check_action_safety(ventilation_action, intelligence)
    print(to_json(ventilation_action))
    print(to_json(ventilation_decision))

    passed = (
        safe_decision.approved is True
        and safe_decision.decision == "approved"
        and safe_decision.risk_level == "low"
        and unsafe_decision.approved is False
        and unsafe_decision.decision == "rejected"
        and unsafe_decision.risk_level in ["high", "critical"]
        and len(unsafe_decision.reasons) > 0
        and unsafe_decision.safe_alternative is not None
        and ventilation_decision.approved is False
        and ventilation_decision.decision == "rejected"
    )

    if passed:
        print("\nPhase 3.1 test passed: Safety Governor approves safe actions and rejects unsafe actions.")
    else:
        print("\nPhase 3.1 test failed: Safety Governor did not meet expected checks.")
        raise SystemExit(1)
