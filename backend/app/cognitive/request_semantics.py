import re
from typing import Any


def extract_next_meeting_minutes(user_message: str) -> int | None:
    text = (user_message or "").lower()
    patterns = [
        r"(?:next|in|after|within)\s+(\d{1,3})\s*(?:mins?|minutes?)",
        r"(\d{1,3})\s*(?:mins?|minutes?)\s+(?:from now|later)",
        r"(?:next|in|after|within)\s+(\d{1,2})\s*(?:hrs?|hours?)",
        r"(\d{1,2})\s*(?:hrs?|hours?)\s+(?:from now|later)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = int(match.group(1))
        token = match.group(0)
        return value * 60 if "hour" in token or "hr" in token else value
    return None


def analyze_user_request(user_message: str) -> dict:
    text = (user_message or "").lower()
    next_meeting_minutes = extract_next_meeting_minutes(text)
    explicitly_empty = any(term in text for term in ["empty", "vacant", "nobody", "unoccupied", "meeting ended"])
    occupied_signal = any(term in text for term in ["meeting room", "people", "person", "we ", "our ", "i am", "i'm"])
    high_temperature = any(term in text for term in ["too hot", "hot", "temperature is high", "high temperature", "overheating", "too warm"])
    low_temperature = any(term in text for term in ["too cold", "freezing", "temperature is low", "low temperature"])
    poor_air = any(term in text for term in ["suffocat", "stuffy", "co2", "air quality", "poor air", "fresh air", "ventilat"])
    poor_light = any(term in text for term in [
        "poor light",
        "poor lighting",
        "lighting is poor",
        "bad light",
        "too dark",
        "dark",
        "can't see",
        "cannot see",
        "can not see",
        "not see clearly",
        "low light",
    ])
    excessive_light = any(term in text for term in ["too bright", "glare", "lights are bright", "excess light"])

    issues = []
    requirements = []
    occupancy = "unoccupied" if explicitly_empty else "occupied" if occupied_signal or any([high_temperature, low_temperature, poor_air, poor_light, excessive_light]) else "unknown"

    if explicitly_empty:
        requirements.append("Treat the affected space as unoccupied; never target occupied zones.")
        requirements.append("Save energy in the empty room with unoccupied-only controls.")
        if next_meeting_minutes is not None:
            requirements.append(
                f"Restore comfort, lighting, and ventilation before the next meeting in {next_meeting_minutes} minutes."
            )

    if high_temperature and occupancy != "unoccupied":
        issues.append("high_temperature")
        requirements.append("Cool the occupied room; do not raise or relax its cooling setpoint.")
    if low_temperature and occupancy != "unoccupied":
        issues.append("low_temperature")
        requirements.append("Warm the occupied room; do not lower its heating effect.")
    if poor_air and occupancy != "unoccupied":
        issues.append("poor_air_quality")
        requirements.append("Increase fresh-air ventilation; do not reduce ventilation.")
    if poor_light and occupancy != "unoccupied":
        issues.append("insufficient_lighting")
        requirements.append("Increase usable lighting; do not dim the lights.")
    if excessive_light and occupancy != "unoccupied":
        issues.append("excessive_lighting")
        requirements.append("Reduce lighting to a usable occupied level.")

    if occupancy == "occupied":
        requirements.insert(0, "Treat the affected space as occupied; never target unoccupied zones.")

    return {
        "original_request": user_message,
        "occupancy": occupancy,
        "explicitly_empty": explicitly_empty,
        "next_meeting_minutes": next_meeting_minutes,
        "issues": issues,
        "requirements": requirements,
        "multi_objective": len(issues) > 1,
    }


def _number(parameters: dict, key: str) -> float | None:
    try:
        value = parameters.get(key)
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def action_semantic_violations(action: dict, analysis: dict) -> list[str]:
    action_type = str(action.get("action_type") or action.get("actionType") or "")
    target = str(action.get("target") or "").lower()
    description = str(action.get("description") or "").lower()
    parameters = action.get("parameters") if isinstance(action.get("parameters"), dict) else {}
    issues = set(analysis.get("issues", []))
    violations = []

    if analysis.get("occupancy") == "occupied" and "unoccupied" in target:
        violations.append("targets unoccupied zones even though the request describes an occupied space")
    if analysis.get("occupancy") == "unoccupied" and "occupied" in target and "unoccupied" not in target:
        violations.append("targets occupied zones even though the request says the space is empty")

    if analysis.get("occupancy") == "unoccupied":
        if action_type == "hvac_setpoint_adjustment":
            cooling = _number(parameters, "cooling_setpoint_c")
            if cooling is not None and cooling < 26:
                violations.append("increases cooling even though the room is empty")
            if any(term in description for term in ["increase cooling", "cool occupied", "comfort recovery"]):
                violations.append("describes occupied comfort recovery even though the room is empty")
        if action_type == "lighting_adjustment":
            level = _number(parameters, "lighting_level_percent")
            if level is not None and level > 50:
                violations.append("keeps lighting high even though the room is empty")
            if any(term in description for term in ["increase usable lighting", "clear visibility"]):
                violations.append("describes occupied lighting recovery even though the room is empty")
        if action_type == "ventilation_adjustment":
            multiplier = _number(parameters, "ventilation_multiplier")
            if multiplier is not None and multiplier > 1:
                violations.append("increases ventilation even though the room is empty")

    if action_type == "hvac_setpoint_adjustment" and "high_temperature" in issues:
        cooling = _number(parameters, "cooling_setpoint_c")
        if cooling is None:
            violations.append("does not provide a cooling_setpoint_c for the high-temperature complaint")
        elif cooling < 23:
            violations.append("sets occupied cooling below the model-safe 23C deadband floor")
        if cooling is not None and cooling > 26:
            violations.append("raises the cooling setpoint despite a high-temperature complaint")
        if any(term in description for term in ["relax", "raise", "increase setpoint"]):
            violations.append("describes reducing cooling despite a high-temperature complaint")

    if action_type == "ventilation_adjustment" and "poor_air_quality" in issues:
        percent = _number(parameters, "ventilation_percent")
        multiplier = _number(parameters, "ventilation_multiplier")
        if multiplier is None:
            violations.append("must use ventilation_multiplier above 1.0 for an air-quality complaint")
        elif multiplier <= 1:
            violations.append("reduces ventilation despite an air-quality complaint")
        elif multiplier > 1.5:
            violations.append("requests a ventilation increase above the safe 1.5 multiplier limit")
        if percent is not None:
            violations.append("uses ambiguous ventilation_percent instead of an increase multiplier")
        if "reduce" in description:
            violations.append("describes reduced ventilation despite an air-quality complaint")

    if action_type == "lighting_adjustment" and "insufficient_lighting" in issues:
        level = _number(parameters, "lighting_level_percent")
        if level is not None and level < 50:
            violations.append("dims lighting despite an insufficient-lighting complaint")
        if any(term in description for term in ["dim", "reduce light"]):
            violations.append("describes dimming despite an insufficient-lighting complaint")

    return list(dict.fromkeys(violations))


def bundle_semantic_violations(bundle: dict, analysis: dict) -> list[str]:
    actions = bundle.get("actions", []) if isinstance(bundle, dict) else []
    action_types = {str(action.get("action_type") or action.get("actionType") or "") for action in actions}
    issues = set(analysis.get("issues", []))
    violations = []

    required_actions = {
        "high_temperature": "hvac_setpoint_adjustment",
        "low_temperature": "hvac_setpoint_adjustment",
        "poor_air_quality": "ventilation_adjustment",
        "insufficient_lighting": "lighting_adjustment",
        "excessive_lighting": "lighting_adjustment",
    }
    if analysis.get("occupancy") == "unoccupied" and not issues:
        for action_type in ["lighting_adjustment", "hvac_setpoint_adjustment"]:
            if action_type not in action_types:
                violations.append(f"missing required {action_type} for empty-room energy saving")
    for issue, action_type in required_actions.items():
        if issue in issues and action_type not in action_types:
            violations.append(f"missing required {action_type} for {issue}")
    for action in actions:
        violations.extend(action_semantic_violations(action, analysis))
    return list(dict.fromkeys(violations))
