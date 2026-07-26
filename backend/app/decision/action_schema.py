import json
import uuid
from dataclasses import asdict, dataclass, is_dataclass


@dataclass
class ControlAction:
    action_id: str
    strategy_name: str
    action_type: str
    target: str
    description: str
    parameters: dict
    expected_energy_saved_percent: float
    expected_carbon_reduced_percent: float
    expected_comfort_impact: str
    source_agent: str
    priority: str


@dataclass
class SafetyDecision:
    action_id: str
    approved: bool
    decision: str
    risk_level: str
    reasons: list[str]
    blocked_by: list[str]
    safe_alternative: dict | None
    checked_constraints: list[str]


def to_dict(obj) -> dict:
    if not is_dataclass(obj):
        raise TypeError("to_dict expects a dataclass object.")
    return asdict(obj)


def to_json(obj) -> str:
    return json.dumps(to_dict(obj), indent=2)


def create_demo_safe_action() -> ControlAction:
    return ControlAction(
        action_id=str(uuid.uuid4()),
        strategy_name="eco_mode",
        action_type="lighting_adjustment",
        target="unoccupied_zones",
        description="Reduce lighting in unoccupied zones to save energy.",
        parameters={
            "lighting_level_percent": 25,
        },
        expected_energy_saved_percent=5.0,
        expected_carbon_reduced_percent=5.0,
        expected_comfort_impact="neutral",
        source_agent="energy_agent",
        priority="medium",
    )


def create_demo_unsafe_action() -> ControlAction:
    return ControlAction(
        action_id=str(uuid.uuid4()),
        strategy_name="aggressive_hvac_cutback",
        action_type="hvac_setpoint_adjustment",
        target="occupied_zones",
        description="Raise occupied cooling setpoint aggressively to maximize savings.",
        parameters={
            "cooling_setpoint_c": 30,
            "applies_to_occupied_zones": True,
        },
        expected_energy_saved_percent=20.0,
        expected_carbon_reduced_percent=20.0,
        expected_comfort_impact="negative",
        source_agent="energy_agent",
        priority="high",
    )
