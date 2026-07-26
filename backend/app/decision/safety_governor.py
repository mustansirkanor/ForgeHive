from backend.app.decision.action_schema import ControlAction, SafetyDecision, to_dict
from backend.app.intelligence.intelligence_api import get_building_intelligence_package


CHECKED_CONSTRAINTS = [
    "hvac_comfort_bounds",
    "lighting_safety",
    "ventilation_iaq",
    "anomaly_severity",
    "expected_impact",
]


def clamp(value, min_value, max_value) -> float:
    return max(min_value, min(float(value), max_value))


def get_current_intelligence() -> dict:
    return get_building_intelligence_package()


def target_includes_occupied(target: str) -> bool:
    normalized = target.lower()
    return "occupied" in normalized and "unoccupied" not in normalized


def evaluate_hvac_safety(action: ControlAction, intelligence: dict) -> list[str]:
    if action.action_type != "hvac_setpoint_adjustment":
        return []

    reasons = []
    cooling_setpoint_c = action.parameters.get("cooling_setpoint_c")
    applies_to_occupied = action.parameters.get("applies_to_occupied_zones", False)
    comfort_status = intelligence.get("comfort", {}).get("status", "Safe")

    if cooling_setpoint_c is not None:
        if cooling_setpoint_c > 26 and applies_to_occupied:
            reasons.append("Cooling setpoint exceeds occupied comfort limit of 26C.")
        if cooling_setpoint_c >= 29 and applies_to_occupied:
            reasons.append("Cooling setpoint is aggressively high and may create comfort risk.")

    if comfort_status in ["Warning", "Unsafe"]:
        reasons.append("Current comfort state is already degraded.")

    return reasons


def evaluate_lighting_safety(action: ControlAction, intelligence: dict) -> list[str]:
    if action.action_type != "lighting_adjustment":
        return []

    reasons = []
    lighting_level = action.parameters.get("lighting_level_percent")

    if lighting_level is None:
        return reasons

    if lighting_level < 20 and target_includes_occupied(action.target):
        reasons.append("Lighting level is too low for occupied zones.")
    if lighting_level < 5:
        reasons.append("Lighting level is extremely low and may be unsafe.")

    return reasons


def evaluate_ventilation_safety(action: ControlAction, intelligence: dict) -> list[str]:
    if action.action_type != "ventilation_adjustment":
        return []

    reasons = []
    ventilation_percent = action.parameters.get("ventilation_percent")
    ventilation_multiplier = action.parameters.get("ventilation_multiplier")
    occupied_zones = intelligence.get("building_state", {}).get("occupancy", {}).get("occupied_zones", 0)
    comfort_status = intelligence.get("comfort", {}).get("status", "Safe")
    anomaly_types = {
        anomaly.get("type")
        for anomaly in intelligence.get("anomalies", {}).get("anomalies", [])
    }

    if ventilation_percent is not None and ventilation_percent < 30 and occupied_zones > 0:
        reasons.append("Ventilation is too low for occupied zones.")
    if ventilation_multiplier is not None and not 0.3 <= float(ventilation_multiplier) <= 1.5:
        reasons.append("Ventilation multiplier is outside the safe 0.3 to 1.5 range.")

    reducing_ventilation = (
        (ventilation_percent is not None and float(ventilation_percent) < 100)
        or (ventilation_multiplier is not None and float(ventilation_multiplier) < 1)
    )
    if reducing_ventilation and (comfort_status in ["Warning", "Unsafe"] or anomaly_types.intersection({"poor_iaq", "elevated_co2"})):
        reasons.append("IAQ risk exists; ventilation reduction is unsafe.")

    return reasons


def evaluate_anomaly_safety(action: ControlAction, intelligence: dict) -> list[str]:
    reasons = []
    highest_severity = intelligence.get("anomalies", {}).get("highest_severity", "none")

    if highest_severity == "critical":
        reasons.append("Critical anomaly exists and action should not proceed automatically.")
    elif highest_severity == "high" and action.priority != "critical":
        reasons.append("High-severity anomaly requires cautious operation.")

    return reasons


def evaluate_expected_impact_safety(action: ControlAction, intelligence: dict) -> list[str]:
    reasons = []

    if action.expected_comfort_impact == "negative" and target_includes_occupied(action.target):
        reasons.append("Action has negative comfort impact on occupied zones.")

    if action.expected_energy_saved_percent > 25:
        reasons.append("Expected energy saving is unusually aggressive and requires review.")

    return reasons


def build_safe_alternative(action: ControlAction, reasons: list[str]) -> dict | None:
    if action.action_type == "hvac_setpoint_adjustment":
        return {
            "strategy_name": "balanced_mode",
            "action_type": "hvac_setpoint_adjustment",
            "description": "Use moderate setpoint adjustment within comfort bounds.",
            "parameters": {
                "cooling_setpoint_c": 24,
                "applies_to_occupied_zones": True,
            },
        }

    if action.action_type == "lighting_adjustment":
        return {
            "strategy_name": "comfort_preserving_lighting",
            "action_type": "lighting_adjustment",
            "description": "Reduce lighting only in unoccupied zones.",
            "parameters": {
                "lighting_level_percent": 25,
                "applies_to_occupied_zones": False,
            },
        }

    return None


def decide_risk_level(reasons: list[str]) -> str:
    if not reasons:
        return "low"
    if len(reasons) == 1:
        return "medium"
    if len(reasons) == 2:
        return "high"
    return "critical"


def check_action_safety(action: ControlAction, intelligence: dict | None = None) -> SafetyDecision:
    current_intelligence = intelligence if intelligence is not None else get_current_intelligence()

    constraint_checks = [
        ("hvac_comfort_bounds", evaluate_hvac_safety),
        ("lighting_safety", evaluate_lighting_safety),
        ("ventilation_iaq", evaluate_ventilation_safety),
        ("anomaly_severity", evaluate_anomaly_safety),
        ("expected_impact", evaluate_expected_impact_safety),
    ]

    reasons = []
    blocked_by = []

    for constraint_name, evaluator in constraint_checks:
        constraint_reasons = evaluator(action, current_intelligence)
        if constraint_reasons:
            blocked_by.append(constraint_name)
            reasons.extend(constraint_reasons)

    if not reasons:
        return SafetyDecision(
            action_id=action.action_id,
            approved=True,
            decision="approved",
            risk_level="low",
            reasons=[],
            blocked_by=[],
            safe_alternative=None,
            checked_constraints=CHECKED_CONSTRAINTS,
        )

    return SafetyDecision(
        action_id=action.action_id,
        approved=False,
        decision="rejected",
        risk_level=decide_risk_level(reasons),
        reasons=reasons,
        blocked_by=blocked_by,
        safe_alternative=build_safe_alternative(action, reasons),
        checked_constraints=CHECKED_CONSTRAINTS,
    )


def check_action_safety_dict(action: ControlAction, intelligence: dict | None = None) -> dict:
    return to_dict(check_action_safety(action, intelligence))
