import json
import uuid
from dataclasses import asdict, dataclass, is_dataclass


ALLOWED_ACTION_TYPES = {
    "lighting_adjustment",
    "hvac_setpoint_adjustment",
    "ventilation_adjustment",
    "equipment_adjustment",
    "carbon_schedule_shift",
    "strategy_mode",
    "preconditioning_schedule",
    "anomaly_response",
    "no_direct_control_change",
}


@dataclass
class CandidateAction:
    action_id: str
    action_type: str
    target: str
    description: str
    parameters: dict
    source: str
    confidence: float


@dataclass
class ActionBundle:
    bundle_id: str
    bundle_name: str
    goal: str
    event_type: str
    actions: list[CandidateAction]
    rationale: str
    constraints: list[str]
    expected_outcome: dict
    created_by: str
    requires_simulation: bool
    fallback_used: bool


@dataclass
class LLMPlanRequest:
    request_id: str
    goal: str
    event_type: str
    building_context: dict
    constraints: list[str]
    max_candidate_bundles: int


@dataclass
class BundleValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    normalized_bundle: dict | None
    safety_notes: list[str]


def to_dict(obj) -> dict:
    if not is_dataclass(obj):
        raise TypeError("to_dict expects a dataclass object.")
    return asdict(obj)


def to_json(obj) -> str:
    return json.dumps(to_dict(obj), indent=2)


def create_candidate_action(
    action_type: str,
    target: str,
    description: str,
    parameters: dict | None = None,
    source: str = "llm_candidate_demo",
    confidence: float = 0.7,
) -> CandidateAction:
    return CandidateAction(
        action_id=str(uuid.uuid4()),
        action_type=action_type,
        target=target,
        description=description,
        parameters=parameters or {},
        source=source,
        confidence=confidence,
    )


def create_demo_empty_room_bundle() -> ActionBundle:
    return ActionBundle(
        bundle_id=str(uuid.uuid4()),
        bundle_name="demo_empty_room_efficiency_bundle",
        goal="reduce waste in empty rooms while preserving safety",
        event_type="demo_sample_only",
        actions=[
            create_candidate_action(
                "lighting_adjustment",
                "unoccupied_zones",
                "Dim lights in unoccupied rooms as a sample candidate action.",
                {"lighting_level_percent": 25},
            ),
            create_candidate_action(
                "hvac_setpoint_adjustment",
                "unoccupied_zones",
                "Relax cooling setpoint in unoccupied rooms as a sample candidate action.",
                {"cooling_setpoint_c": 26},
            ),
            create_candidate_action(
                "ventilation_adjustment",
                "unoccupied_zones",
                "Reduce ventilation moderately in unoccupied rooms as a sample candidate action.",
                {"ventilation_percent": 40},
            ),
        ],
        rationale=(
            "Demo bundle only. Final selection happens later after simulation, "
            "RL ranking, and safety checks."
        ),
        constraints=[
            "Do not execute directly.",
            "Validate schema before ranking.",
            "Safety Governor approval required before execution.",
        ],
        expected_outcome={
            "energy_saved_percent": 4.0,
            "comfort_impact": "neutral",
            "requires_layer5_simulation": True,
        },
        created_by="layer_4_1_demo_contract",
        requires_simulation=True,
        fallback_used=False,
    )


def get_action_bundle_schema() -> dict:
    return {
        "ActionBundle": {
            "bundle_id": "str",
            "bundle_name": "str",
            "goal": "str",
            "event_type": "str",
            "actions": "list[CandidateAction]",
            "rationale": "str",
            "constraints": "list[str]",
            "expected_outcome": "dict",
            "created_by": "str",
            "requires_simulation": "bool",
            "fallback_used": "bool",
        },
        "CandidateAction": {
            "action_id": "str",
            "action_type": sorted(ALLOWED_ACTION_TYPES),
            "target": "str",
            "description": "str",
            "parameters": "dict",
            "source": "str",
            "confidence": "float 0..1",
        },
        "note": "This schema validates LLM output format only. Safety Governor approval is still required.",
    }


def bundle_to_dict(bundle: ActionBundle | dict) -> dict:
    if is_dataclass(bundle):
        return to_dict(bundle)
    if isinstance(bundle, dict):
        return bundle
    raise TypeError("bundle must be an ActionBundle or dict.")


def target_includes_occupied(target: str) -> bool:
    normalized = str(target).lower()
    return "occupied" in normalized and "unoccupied" not in normalized


def validate_numeric_range(
    value,
    min_value: float,
    max_value: float,
    field_name: str,
    errors: list[str],
) -> float | None:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        errors.append(f"{field_name} must be numeric.")
        return None

    if not min_value <= numeric_value <= max_value:
        errors.append(f"{field_name} must be between {min_value:g} and {max_value:g}.")
    return numeric_value


def validate_action_bundle(bundle: ActionBundle | dict) -> BundleValidationResult:
    errors = []
    warnings = []
    safety_notes = [
        "Action bundle validation does not replace the Safety Governor.",
        "Validated bundles still require simulation/ranking and final safety approval.",
        "Layer 4.1 does not execute actions.",
    ]

    try:
        normalized_bundle = bundle_to_dict(bundle)
    except TypeError as exc:
        return BundleValidationResult(False, [str(exc)], warnings, None, safety_notes)

    actions = normalized_bundle.get("actions")
    if not isinstance(actions, list):
        errors.append("actions must be a list.")
        actions = []

    if len(actions) == 0:
        errors.append("bundle must have at least one action.")
    if len(actions) > 8:
        errors.append("bundle must not have more than 8 actions.")

    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            errors.append(f"actions[{index}] must be an object.")
            continue

        action_type = action.get("action_type")
        target = action.get("target", "")
        parameters = action.get("parameters") or {}

        if action_type not in ALLOWED_ACTION_TYPES:
            errors.append(f"actions[{index}].action_type is not allowed: {action_type}")

        if not isinstance(parameters, dict):
            errors.append(f"actions[{index}].parameters must be an object.")
            parameters = {}

        confidence = action.get("confidence")
        validate_numeric_range(confidence, 0, 1, f"actions[{index}].confidence", errors)

        if action_type == "no_direct_control_change":
            continue

        if "lighting_level_percent" in parameters:
            lighting_level = validate_numeric_range(
                parameters["lighting_level_percent"],
                0,
                100,
                f"actions[{index}].parameters.lighting_level_percent",
                errors,
            )
            if lighting_level is not None and target_includes_occupied(target) and lighting_level < 20:
                warnings.append("Occupied-zone lighting below 20% may be uncomfortable or unsafe.")

        if "cooling_setpoint_c" in parameters:
            cooling_setpoint = validate_numeric_range(
                parameters["cooling_setpoint_c"],
                18,
                30,
                f"actions[{index}].parameters.cooling_setpoint_c",
                errors,
            )
            if cooling_setpoint is not None and target_includes_occupied(target) and cooling_setpoint > 26:
                warnings.append("Occupied-zone cooling setpoint above 26C may affect comfort.")

        if "heating_setpoint_c" in parameters:
            validate_numeric_range(
                parameters["heating_setpoint_c"],
                16,
                24,
                f"actions[{index}].parameters.heating_setpoint_c",
                errors,
            )

        if "ventilation_percent" in parameters:
            ventilation_percent = validate_numeric_range(
                parameters["ventilation_percent"],
                20,
                100,
                f"actions[{index}].parameters.ventilation_percent",
                errors,
            )
            if ventilation_percent is not None and ventilation_percent < 30:
                warnings.append("Ventilation below 30% may create IAQ risk.")

        if "ventilation_multiplier" in parameters:
            validate_numeric_range(
                parameters["ventilation_multiplier"],
                0.3,
                1.5,
                f"actions[{index}].parameters.ventilation_multiplier",
                errors,
            )

    return BundleValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        normalized_bundle=normalized_bundle if len(errors) == 0 else None,
        safety_notes=safety_notes,
    )
