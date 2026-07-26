import re
from copy import deepcopy


def clamp_number(value, minimum: float, maximum: float, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(minimum, min(maximum, numeric))


def read_first_number(parameters: dict, keys: list[str], default=None):
    for key in keys:
        if key in parameters:
            return parameters[key]
    return default


def target_includes_occupied(target: str) -> bool:
    normalized = str(target or "").lower()
    return "occupied" in normalized and "unoccupied" not in normalized


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "bundle")).strip("_").lower()
    return slug[:60] or "bundle"


def normalize_bundle_for_simulation(bundle: dict) -> dict:
    normalized = deepcopy(bundle or {})
    normalized.setdefault("bundle_id", normalized.get("bundle_name", "candidate_bundle"))
    normalized.setdefault("bundle_name", normalized.get("bundle_id", "candidate_bundle"))
    normalized.setdefault("goal", "balanced_optimization")
    normalized.setdefault("event_type", "operator_request")
    normalized.setdefault("actions", [])
    normalized.setdefault("created_by", "layer4_candidate")
    normalized.setdefault("requires_simulation", True)
    return normalized


def strategy_name_from_bundle(bundle: dict, strategy: dict) -> str:
    name = str(bundle.get("bundle_name", "")).lower()
    action_types = {action.get("action_type") for action in bundle.get("actions", [])}
    if "carbon_schedule_shift" in action_types:
        return "carbon_aware_mode"
    if "aggressive" in name:
        return "eco_mode_aggressive"
    if "conservative" in name:
        return "eco_mode_conservative"
    if "strategy_mode" in action_types and strategy.get("strategy_mode"):
        return str(strategy["strategy_mode"])
    if {"lighting_adjustment", "hvac_setpoint_adjustment", "ventilation_adjustment"}.intersection(action_types):
        return "eco_mode"
    return "balanced_mode"


def derive_simulation_strategy_from_bundle(bundle: dict) -> dict:
    normalized = normalize_bundle_for_simulation(bundle)
    notes = []
    strategy = {
        "strategy_name": "",
        "safe_description": f"Simulation strategy derived from bundle {normalized.get('bundle_name')}.",
        "actions_used": [],
        "idf_adapter_targets": {
            "lighting_adjustment": False,
            "hvac_setpoint_adjustment": False,
            "ventilation_adjustment": False,
        },
        "simulation_notes": notes,
    }

    for action in normalized.get("actions", []):
        action_type = action.get("action_type")
        parameters = action.get("parameters") if isinstance(action.get("parameters"), dict) else {}
        target = action.get("target", "")
        strategy["actions_used"].append(
            {
                "action_type": action_type,
                "target": target,
                "parameters": parameters,
                "description": action.get("description", ""),
            }
        )

        if action_type == "lighting_adjustment":
            strategy["idf_adapter_targets"]["lighting_adjustment"] = True
            raw_value = read_first_number(parameters, ["lighting_level_percent", "brightness", "value"])
            if raw_value is None and "reduction_percent" in parameters:
                raw_value = 100 - float(parameters.get("reduction_percent") or 0)
            if raw_value is None:
                raw_value = 35
                notes.append("Lighting value was ambiguous; defaulted to 35 percent for simulation.")
            strategy["lighting_level_percent"] = clamp_number(raw_value, 10, 100, 35)

        elif action_type == "hvac_setpoint_adjustment":
            strategy["idf_adapter_targets"]["hvac_setpoint_adjustment"] = True
            raw_value = parameters.get("cooling_setpoint_c")
            if raw_value is None:
                if "value" in parameters:
                    raw_value = parameters["value"]
                elif "increase_by" in parameters:
                    raw_value = 24 + float(parameters.get("increase_by") or 0)
            if raw_value is None:
                raw_value = 26 if target_includes_occupied(target) else 28
                notes.append("HVAC setpoint was ambiguous; defaulted conservatively for simulation.")
            max_setpoint = 26 if target_includes_occupied(target) else 30
            min_setpoint = 23 if target_includes_occupied(target) else 21
            strategy["cooling_setpoint_c"] = clamp_number(raw_value, min_setpoint, max_setpoint, 26)
            if "heating_setpoint_c" in parameters:
                strategy["heating_setpoint_c"] = clamp_number(parameters["heating_setpoint_c"], 16, 24, 20)

        elif action_type == "ventilation_adjustment":
            strategy["idf_adapter_targets"]["ventilation_adjustment"] = True
            if "ventilation_multiplier" in parameters:
                strategy["ventilation_multiplier"] = clamp_number(
                    parameters["ventilation_multiplier"], 0.3, 1.5, 1.0
                )
            else:
                raw_value = read_first_number(parameters, ["ventilation_percent", "value"], 40)
                if raw_value is None:
                    notes.append("Ventilation value was ambiguous; defaulted to 40 percent for simulation.")
                strategy["ventilation_percent"] = clamp_number(raw_value, 30, 100, 40)

        elif action_type == "carbon_schedule_shift":
            strategy["carbon_shift_enabled"] = True

        elif action_type == "strategy_mode":
            strategy["strategy_mode"] = parameters.get("mode", parameters.get("value", "balanced_mode"))

        elif action_type == "preconditioning_schedule":
            strategy["preconditioning_schedule"] = parameters
            notes.append("Preconditioning schedule recorded as metadata for timed recovery before future occupancy.")

        elif action_type == "no_direct_control_change":
            notes.append("No-direct-control action recorded as metadata; no IDF modification requested.")

        else:
            notes.append(f"Action type {action_type} is not directly simulated; left unchanged.")

    strategy["strategy_name"] = strategy_name_from_bundle(normalized, strategy)
    return strategy
