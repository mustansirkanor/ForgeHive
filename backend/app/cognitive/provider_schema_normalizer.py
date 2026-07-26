import copy

from backend.app.cognitive.action_bundle_schema import validate_action_bundle


CANONICAL_ACTION_TYPES = {
    "lighting_adjustment",
    "hvac_setpoint_adjustment",
    "ventilation_adjustment",
    "carbon_schedule_shift",
    "strategy_mode",
    "preconditioning_schedule",
    "no_direct_control_change",
}


ACTION_TYPE_ALIASES = {
    "occupancy_based_control": "strategy_mode",
    "occupancy_control": "strategy_mode",
    "occupancy_schedule_adjustment": "strategy_mode",
    "lighting_control": "lighting_adjustment",
    "lights_adjustment": "lighting_adjustment",
    "light_adjustment": "lighting_adjustment",
    "dim_lights": "lighting_adjustment",
    "hvac_adjustment": "hvac_setpoint_adjustment",
    "setpoint_adjustment": "hvac_setpoint_adjustment",
    "temperature_adjustment": "hvac_setpoint_adjustment",
    "ventilation_control": "ventilation_adjustment",
    "iaq_control": "ventilation_adjustment",
    "air_quality_adjustment": "ventilation_adjustment",
    "carbon_aware_scheduling": "carbon_schedule_shift",
    "load_shift": "carbon_schedule_shift",
    "carbon_shift": "carbon_schedule_shift",
    "comfort_mode": "strategy_mode",
    "safety_mode": "strategy_mode",
    "preconditioning": "preconditioning_schedule",
    "precondition": "preconditioning_schedule",
    "restore_before_meeting": "preconditioning_schedule",
    "meeting_recovery": "preconditioning_schedule",
    "do_nothing": "no_direct_control_change",
    "no_action": "no_direct_control_change",
}


def target_default_for_event(event_type: str) -> str:
    if event_type == "empty_room_detected":
        return "unoccupied_zones"
    if event_type == "iaq_risk_detected":
        return "affected_zones"
    if event_type == "high_carbon_window":
        return "flexible_loads"
    if event_type == "comfort_request":
        return "occupied_zones"
    if event_type == "anomaly_detected":
        return "affected_equipment"
    return "building"


def normalize_action_type(action_type) -> str | None:
    normalized = str(action_type or "").strip().lower()
    if normalized in CANONICAL_ACTION_TYPES:
        return normalized
    return ACTION_TYPE_ALIASES.get(normalized)


def normalize_expected_outcome(value, notes: list[str], bundle_index: int) -> dict:
    if value is None:
        notes.append(f"candidate_bundles[{bundle_index}].expected_outcome defaulted to empty object.")
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        notes.append(f"candidate_bundles[{bundle_index}].expected_outcome string converted to object.")
        return {"summary": value}
    if isinstance(value, (int, float)):
        notes.append(f"candidate_bundles[{bundle_index}].expected_outcome number converted to object.")
        return {"estimated_value": value}
    if isinstance(value, list):
        notes.append(f"candidate_bundles[{bundle_index}].expected_outcome list converted to object.")
        return {"items": value}
    notes.append(f"candidate_bundles[{bundle_index}].expected_outcome unsupported type converted to empty object.")
    return {}


def normalize_constraints(value, notes: list[str], bundle_index: int) -> list:
    if value is None:
        notes.append(f"candidate_bundles[{bundle_index}].constraints defaulted to empty list.")
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (str, dict)):
        notes.append(f"candidate_bundles[{bundle_index}].constraints converted to list.")
        return [value]
    notes.append(f"candidate_bundles[{bundle_index}].constraints unsupported type converted to empty list.")
    return []


def normalize_confidence(value, notes: list[str], bundle_index: int, action_index: int) -> float:
    if value is None:
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].confidence defaulted to 0.65.")
        return 0.65
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].confidence invalid; defaulted to 0.65.")
        return 0.65
    clamped = max(0.0, min(1.0, confidence))
    if clamped != confidence:
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].confidence clamped to {clamped}.")
    return clamped


def normalize_parameters(raw_action: dict, notes: list[str], bundle_index: int, action_index: int) -> dict:
    parameters = raw_action.get("parameters")
    if not isinstance(parameters, dict):
        parameters = {}
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].parameters defaulted to empty object.")
    else:
        parameters = copy.deepcopy(parameters)

    if "action_value" in raw_action:
        parameters["value"] = raw_action.get("action_value")
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].action_value moved into parameters.value.")
    elif "value" in raw_action and "value" not in parameters:
        parameters["value"] = raw_action.get("value")
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].value moved into parameters.value.")

    return parameters


def normalize_action(raw_action: dict, provider: str, event_type: str, bundle_index: int, action_index: int, notes: list[str], dropped_actions: list[dict]) -> dict | None:
    if not isinstance(raw_action, dict):
        dropped_actions.append({"bundle_index": bundle_index, "action_index": action_index, "reason": "action is not an object"})
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}] dropped because it is not an object.")
        return None

    canonical_type = normalize_action_type(raw_action.get("action_type"))
    if canonical_type is None:
        dropped_actions.append(
            {
                "bundle_index": bundle_index,
                "action_index": action_index,
                "action_type": raw_action.get("action_type"),
                "reason": "unknown action_type",
            }
        )
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}] dropped unknown action_type {raw_action.get('action_type')}.")
        return None

    if canonical_type != raw_action.get("action_type"):
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].action_type normalized to {canonical_type}.")

    description = raw_action.get("description")
    if not description:
        description = f"Candidate {canonical_type} for simulation and safety review."
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].description defaulted.")

    target = raw_action.get("target")
    if not target:
        target = target_default_for_event(event_type)
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].target defaulted to {target}.")

    source = raw_action.get("source")
    if not source:
        source = "llm_generated"
        notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].source defaulted.")

    return {
        "action_type": canonical_type,
        "target": target,
        "description": description,
        "parameters": normalize_parameters(raw_action, notes, bundle_index, action_index),
        "source": source,
        "confidence": normalize_confidence(raw_action.get("confidence"), notes, bundle_index, action_index),
    }


def bundle_level_action_fields(bundle: dict) -> dict | None:
    if "action_type" not in bundle:
        return None
    action = {}
    for field in ["action_type", "target", "description", "parameters", "action_value", "value", "source", "confidence"]:
        if field in bundle:
            action[field] = bundle[field]
    return action


def normalize_bundle(raw_bundle: dict, provider: str, goal: str, event_type: str, bundle_index: int, notes: list[str], dropped_actions: list[dict], dropped_bundles: list[dict]) -> dict | None:
    if not isinstance(raw_bundle, dict):
        dropped_bundles.append({"bundle_index": bundle_index, "reason": "bundle is not an object"})
        notes.append(f"candidate_bundles[{bundle_index}] dropped because it is not an object.")
        return None

    bundle = copy.deepcopy(raw_bundle)
    bundle_name = bundle.get("bundle_name") or bundle.get("bundle_id") or bundle.get("id") or bundle.get("name")
    if not bundle_name:
        dropped_bundles.append({"bundle_index": bundle_index, "reason": "missing bundle_name"})
        notes.append(f"candidate_bundles[{bundle_index}] dropped because bundle_name is missing.")
        return None
    if "bundle_name" not in bundle:
        notes.append(f"candidate_bundles[{bundle_index}].bundle_name recovered from alternate id/name field.")

    raw_actions = bundle.get("actions")
    if not isinstance(raw_actions, list) or len(raw_actions) == 0:
        recovered_action = bundle_level_action_fields(bundle)
        if recovered_action is None:
            dropped_bundles.append({"bundle_index": bundle_index, "bundle_name": str(bundle_name), "reason": "no recoverable actions"})
            notes.append(f"candidate_bundles[{bundle_index}] dropped because it has no recoverable actions.")
            return None
        raw_actions = [recovered_action]
        notes.append(f"candidate_bundles[{bundle_index}].actions recovered from bundle-level action fields.")

    actions = []
    for action_index, raw_action in enumerate(raw_actions):
        normalized_action = normalize_action(raw_action, provider, event_type, bundle_index, action_index, notes, dropped_actions)
        if normalized_action is not None:
            actions.append(normalized_action)

    if not actions:
        dropped_bundles.append({"bundle_index": bundle_index, "bundle_name": str(bundle_name), "reason": "all actions dropped"})
        notes.append(f"candidate_bundles[{bundle_index}] dropped because all actions were unknown or invalid.")
        return None

    normalized_bundle = {
        "bundle_name": str(bundle_name),
        "goal": bundle.get("goal") or goal,
        "event_type": bundle.get("event_type") or event_type,
        "actions": actions,
        "rationale": bundle.get("rationale") or "Generated candidate bundle for simulation and safety review.",
        "constraints": normalize_constraints(bundle.get("constraints"), notes, bundle_index),
        "expected_outcome": normalize_expected_outcome(bundle.get("expected_outcome"), notes, bundle_index),
        "created_by": bundle.get("created_by") or f"{provider}_llm_candidate_generator",
        "requires_simulation": bundle.get("requires_simulation") if bundle.get("requires_simulation") is not None else True,
        "fallback_used": bundle.get("fallback_used") if bundle.get("fallback_used") is not None else False,
    }

    validation = validate_action_bundle(normalized_bundle)
    if not validation.valid:
        dropped_bundles.append(
            {
                "bundle_index": bundle_index,
                "bundle_name": str(bundle_name),
                "reason": "validation failed",
                "errors": validation.errors,
            }
        )
        notes.append(f"candidate_bundles[{bundle_index}] dropped after validation: {'; '.join(validation.errors)}")
        return None

    return normalized_bundle


def normalize_llm_candidate_response(parsed_response: dict, provider: str, goal: str, event_type: str) -> dict:
    repair_notes = []
    dropped_actions = []
    dropped_bundles = []

    candidate_bundles = parsed_response.get("candidate_bundles") if isinstance(parsed_response, dict) else None
    raw_bundle_count = len(candidate_bundles) if isinstance(candidate_bundles, list) else 0
    if not isinstance(candidate_bundles, list) or not candidate_bundles:
        return {
            "normalized_response": {"candidate_bundles": []},
            "schema_repair_applied": False,
            "repair_notes": ["candidate_bundles is missing or empty."],
            "dropped_actions": dropped_actions,
            "dropped_bundles": dropped_bundles,
            "normalized_bundle_count": 0,
            "raw_bundle_count": raw_bundle_count,
        }

    normalized_bundles = []
    for bundle_index, raw_bundle in enumerate(candidate_bundles):
        normalized_bundle = normalize_bundle(
            raw_bundle,
            provider,
            goal,
            event_type,
            bundle_index,
            repair_notes,
            dropped_actions,
            dropped_bundles,
        )
        if normalized_bundle is not None:
            normalized_bundles.append(normalized_bundle)

    return {
        "normalized_response": {"candidate_bundles": normalized_bundles},
        "schema_repair_applied": bool(repair_notes or dropped_actions or dropped_bundles),
        "repair_notes": repair_notes,
        "dropped_actions": dropped_actions,
        "dropped_bundles": dropped_bundles,
        "normalized_bundle_count": len(normalized_bundles),
        "raw_bundle_count": raw_bundle_count,
    }
