import json
import uuid
from itertools import product

from backend.app.cognitive.action_bundle_schema import (
    ActionBundle,
    create_candidate_action,
    to_dict,
    validate_action_bundle,
)
from backend.app.cognitive.knowledge_graph import (
    get_relevant_knowledge_context,
    record_candidate_bundle_to_kg,
)
from backend.app.cognitive.llm_client import (
    call_mock_llm,
    call_llm,
    extract_json_from_llm_text,
)
from backend.app.cognitive.request_semantics import action_semantic_violations, bundle_semantic_violations
from backend.app.experience.experience_retriever import retrieve_similar_experiences
from backend.app.experience.llm_context_builder import build_experience_context_for_llm
from backend.app.experience.similarity import extract_situation_signature_from_context


GUARDRAILS = [
    "Bundles are candidates only.",
    "Layer 4 does not execute actions.",
    "Layer 5 must simulate and rank candidate bundles.",
    "Safety Governor approval is required before execution.",
]


def build_candidate_generation_context(goal: str, event_type: str = "operator_request", extra_context: dict | None = None) -> dict:
    from backend.app.cognitive.mcp_tool_registry import execute_mcp_tool

    intelligence_result = execute_mcp_tool("get_building_intelligence_package")
    building_context = intelligence_result.get("result", {}) if intelligence_result.get("success") else {}
    knowledge_context = get_relevant_knowledge_context(goal, event_type, building_context)
    situation_signature = extract_situation_signature_from_context(
        {
            "goal": goal,
            "event_type": event_type,
            "building_context": building_context,
            "extra_context": extra_context or {},
            **(extra_context or {}),
        }
    )
    experience_retrieval = retrieve_similar_experiences(situation_signature)
    experience_context = build_experience_context_for_llm(experience_retrieval)
    return {
        "goal": goal,
        "event_type": event_type,
        "building_context": building_context,
        "knowledge_context": knowledge_context,
        "situation_signature": situation_signature,
        "experience_retrieval": experience_retrieval,
        "experience_context_for_llm": experience_context,
        "constraints": [
            "comfort must remain safe",
            "occupied-zone lighting must remain usable",
            "CO2/IAQ risk must not increase",
            "execution disabled until Layer 5",
            "every bundle must pass validation and Safety Governor",
            "EnergyPlus simulation required before execution",
        ],
        "extra_context": extra_context or {},
    }


def build_candidate_generation_prompt(context: dict) -> str:
    analysis = context.get("extra_context", {}).get("request_analysis", {})
    issue_to_action = {
        "high_temperature": "hvac_setpoint_adjustment",
        "low_temperature": "hvac_setpoint_adjustment",
        "poor_air_quality": "ventilation_adjustment",
        "insufficient_lighting": "lighting_adjustment",
        "excessive_lighting": "lighting_adjustment",
    }
    required_action_types = list(dict.fromkeys(
        issue_to_action[issue]
        for issue in analysis.get("issues", [])
        if issue in issue_to_action
    ))
    if analysis.get("occupancy") == "unoccupied" and not required_action_types:
        required_action_types = [
            "lighting_adjustment",
            "hvac_setpoint_adjustment",
        ]
        if analysis.get("next_meeting_minutes") is not None:
            required_action_types.append("preconditioning_schedule")
    required_target = (
        "occupied_zones"
        if analysis.get("occupancy") == "occupied"
        else "unoccupied_zones"
        if analysis.get("occupancy") == "unoccupied"
        else "affected_zones"
    )
    example = {
        "candidate_bundles": [
            {
                "bundle_name": "example_bundle",
                "goal": context["goal"],
                "event_type": context["event_type"],
                "actions": [
                    {
                        "action_type": "strategy_mode",
                        "target": "affected_zones",
                        "description": "Schema example only; replace this with request-specific actions.",
                        "parameters": {"mode": "request_specific_mode"},
                        "source": "llm_generated",
                        "confidence": 0.7,
                    }
                ],
                "rationale": "Explain why this candidate may help.",
                "constraints": context["constraints"],
                "expected_outcome": {},
                "created_by": "llm_candidate_generator",
                "requires_simulation": True,
                "fallback_used": False,
            }
        ]
    }
    return (
        f"Context JSON:\n{json.dumps(context, indent=2)}\n\n"
        f"Experience Graph advisory context:\n{context.get('experience_context_for_llm', '')}\n\n"
        "Previous experiences are advisory. Current safety rules override history. Safety Governor remains final authority. "
        "Real building execution is not allowed.\n"
        f"Original operator request: {context.get('extra_context', {}).get('operator_request', '')}\n"
        f"Mandatory request requirements: {json.dumps(context.get('extra_context', {}).get('required_outcomes', []))}\n"
        f"Required action_type values in EVERY candidate bundle: {json.dumps(required_action_types)}\n"
        f"Required target for request-specific control actions: {required_target}\n"
        "A candidate is invalid if even one required action_type is missing. Each required action must use the required target.\n"
        "Every candidate bundle must address every detected issue in the original request. Preserve occupied/unoccupied context. "
        "Never propose an action opposite to the request (for example, never dim for poor lighting, reduce ventilation for suffocating air, or reduce cooling for a hot room). "
        "For empty-room or meeting-ended requests, target unoccupied_zones only; save energy by dimming lights and relaxing the unoccupied cooling setpoint. Add safe ventilation reduction when available. Never cool occupied zones for an empty room. "
        "If the request mentions a future meeting time, include a preconditioning_schedule action that restores comfort, lighting, and ventilation before occupants arrive. "
        "For occupied high-temperature requests, use cooling_setpoint_c from 23 through 26. "
        "For poor-air or stuffy requests, use ventilation_multiplier from 1.1 through 1.5; do not use ventilation_percent. "
        "The schema example below is not a suggested action; do not copy its name, target, or values.\n"
        "Return only JSON. Generate 2 to 5 bundles. Use multiple actions per bundle when appropriate. "
        "Do not execute actions. Do not claim results as actual. Values are proposed candidates only.\n"
        f"Required shape:\n{json.dumps(example, indent=2)}"
    )


def safe_confidence(value, default: float = 0.5) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, confidence))


def normalize_llm_bundle(raw_bundle: dict, goal: str, event_type: str) -> ActionBundle:
    actions = []
    for raw_action in raw_bundle.get("actions", []):
        if not isinstance(raw_action, dict):
            continue
        parameters = raw_action.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}
        actions.append(
            create_candidate_action(
                action_type=raw_action.get("action_type", "no_direct_control_change"),
                target=raw_action.get("target", "whole_building"),
                description=raw_action.get("description", "Candidate action."),
                parameters=parameters,
                source=raw_action.get("source", "llm_generated"),
                confidence=safe_confidence(raw_action.get("confidence", 0.5)),
            )
        )

    return ActionBundle(
        bundle_id=raw_bundle.get("bundle_id", str(uuid.uuid4())),
        bundle_name=raw_bundle.get("bundle_name", "llm_candidate_bundle"),
        goal=raw_bundle.get("goal", goal),
        event_type=raw_bundle.get("event_type", event_type),
        actions=actions,
        rationale=raw_bundle.get("rationale", ""),
        constraints=raw_bundle.get("constraints", []),
        expected_outcome=raw_bundle.get("expected_outcome", {}),
        created_by=raw_bundle.get("created_by", "llm_candidate_generator"),
        requires_simulation=bool(raw_bundle.get("requires_simulation", True)),
        fallback_used=bool(raw_bundle.get("fallback_used", False)),
    )


def compose_complete_llm_bundles(bundles: list[ActionBundle], context: dict, max_bundles: int = 3) -> list[ActionBundle]:
    analysis = context.get("extra_context", {}).get("request_analysis", {})
    issue_to_action = {
        "high_temperature": "hvac_setpoint_adjustment",
        "low_temperature": "hvac_setpoint_adjustment",
        "poor_air_quality": "ventilation_adjustment",
        "insufficient_lighting": "lighting_adjustment",
        "excessive_lighting": "lighting_adjustment",
    }
    required_types = list(dict.fromkeys(
        issue_to_action[issue]
        for issue in analysis.get("issues", [])
        if issue in issue_to_action
    ))
    if len(required_types) < 2:
        return []

    actions_by_type: dict[str, list[dict]] = {action_type: [] for action_type in required_types}
    for bundle in bundles:
        bundle_dict = to_dict(bundle)
        for action in bundle_dict.get("actions", []):
            action_type = action.get("action_type")
            if action_type in actions_by_type and not action_semantic_violations(action, analysis):
                actions_by_type[action_type].append(action)

    if any(not actions_by_type[action_type] for action_type in required_types):
        return []

    for action_type in required_types:
        actions_by_type[action_type].sort(key=lambda action: float(action.get("confidence", 0) or 0), reverse=True)

    composed = []
    seen = set()
    action_choices = [actions_by_type[action_type][:max_bundles] for action_type in required_types]
    for index, combination in enumerate(product(*action_choices), start=1):
        signature = json.dumps(
            [{"type": action.get("action_type"), "target": action.get("target"), "parameters": action.get("parameters", {})} for action in combination],
            sort_keys=True,
        )
        if signature in seen:
            continue
        seen.add(signature)
        raw_bundle = {
            "bundle_name": f"llm_composed_plan_{index}",
            "goal": context["goal"],
            "event_type": context["event_type"],
            "actions": list(combination),
            "rationale": "Composed from compatible request-aligned actions proposed by the LLM across its candidate plans.",
            "constraints": context["constraints"],
            "expected_outcome": {"comfort_impact": "positive"},
            "created_by": "llm_plan_composer",
            "requires_simulation": True,
            "fallback_used": False,
        }
        composed.append(normalize_llm_bundle(raw_bundle, context["goal"], context["event_type"]))
        if len(composed) >= max_bundles:
            break
    return composed


def repair_empty_room_bundles(bundles: list[ActionBundle], context: dict) -> list[ActionBundle]:
    analysis = context.get("extra_context", {}).get("request_analysis", {})
    if analysis.get("occupancy") != "unoccupied":
        return bundles
    next_meeting_minutes = analysis.get("next_meeting_minutes") or context.get("extra_context", {}).get("next_meeting_minutes")

    repaired = []
    for bundle in bundles:
        bundle_dict = to_dict(bundle)
        actions = []
        by_type = {action.get("action_type"): action for action in bundle_dict.get("actions", [])}

        lighting = by_type.get("lighting_adjustment") or {
            "action_type": "lighting_adjustment",
            "target": "unoccupied_zones",
            "description": "Reduce unoccupied lighting because the room is empty.",
            "parameters": {"lighting_level_percent": 25},
            "source": "semantic_repair_controller",
            "confidence": 0.72,
        }
        hvac = by_type.get("hvac_setpoint_adjustment") or {
            "action_type": "hvac_setpoint_adjustment",
            "target": "unoccupied_zones",
            "description": "Relax unoccupied cooling setpoint because the room is empty.",
            "parameters": {"cooling_setpoint_c": 28, "applies_to_occupied_zones": False},
            "source": "semantic_repair_controller",
            "confidence": 0.72,
        }
        ventilation = by_type.get("ventilation_adjustment") or {
            "action_type": "ventilation_adjustment",
            "target": "unoccupied_zones",
            "description": "Reduce ventilation within safe empty-room bounds.",
            "parameters": {"ventilation_percent": 40},
            "source": "semantic_repair_controller",
            "confidence": 0.68,
        }

        for action in [lighting, hvac, ventilation]:
            fixed = json.loads(json.dumps(action))
            fixed["target"] = "unoccupied_zones"
            fixed.setdefault("source", "semantic_repair_controller")
            fixed["confidence"] = safe_confidence(fixed.get("confidence", 0.7))
            if fixed.get("action_type") == "lighting_adjustment":
                fixed.setdefault("parameters", {})
                fixed["parameters"]["lighting_level_percent"] = min(float(fixed["parameters"].get("lighting_level_percent", 25) or 25), 50)
            if fixed.get("action_type") == "hvac_setpoint_adjustment":
                fixed.setdefault("parameters", {})
                fixed["parameters"]["cooling_setpoint_c"] = max(float(fixed["parameters"].get("cooling_setpoint_c", 28) or 28), 26)
                fixed["parameters"]["applies_to_occupied_zones"] = False
            if fixed.get("action_type") == "ventilation_adjustment":
                fixed.setdefault("parameters", {})
                fixed["parameters"].pop("ventilation_multiplier", None)
                fixed["parameters"].setdefault("ventilation_percent", 40)
            actions.append(fixed)

        if next_meeting_minutes is not None:
            restore_minutes_before = 20 if int(next_meeting_minutes) >= 45 else 10
            actions.append(
                {
                    "action_type": "preconditioning_schedule",
                    "target": "meeting_room",
                    "description": (
                        f"Restore comfort, lighting, and fresh-air readiness {restore_minutes_before} minutes before "
                        f"the next meeting in {int(next_meeting_minutes)} minutes."
                    ),
                    "parameters": {
                        "next_meeting_minutes": int(next_meeting_minutes),
                        "restore_minutes_before_meeting": restore_minutes_before,
                        "restore_lighting_level_percent": 70,
                        "restore_cooling_setpoint_c": 24,
                        "restore_ventilation_multiplier": 1.0,
                        "execution_mode": "scheduled_metadata_for_digital_twin",
                    },
                    "source": "semantic_repair_controller",
                    "confidence": 0.76,
                }
            )

        raw_bundle = {
            **bundle_dict,
            "bundle_name": bundle_dict.get("bundle_name") or "empty_room_repaired_llm_plan",
            "actions": actions,
            "rationale": (
                (bundle_dict.get("rationale") or "LLM generated an empty-room candidate.")
                + " Semantic repair completed missing unoccupied-only energy actions before simulation."
            ),
            "created_by": "llm_empty_room_semantic_repair",
            "fallback_used": False,
        }
        repaired.append(normalize_llm_bundle(raw_bundle, context["goal"], context["event_type"]))

    return repaired or bundles


def make_bundle(name: str, context: dict, actions: list, outcome: dict) -> ActionBundle:
    return ActionBundle(
        bundle_id=str(uuid.uuid4()),
        bundle_name=name,
        goal=context["goal"],
        event_type=context["event_type"],
        actions=actions,
        rationale="Deterministic fallback candidate. It must still be simulated, ranked, and safety-checked.",
        constraints=context["constraints"],
        expected_outcome=outcome,
        created_by="fallback_candidate_generator",
        requires_simulation=True,
        fallback_used=True,
    )


def generate_fallback_candidate_bundles(context: dict) -> list[ActionBundle]:
    analysis = context.get("extra_context", {}).get("request_analysis", {})
    if analysis.get("issues"):
        parsed = extract_json_from_llm_text(call_mock_llm("", context))
        return [
            normalize_llm_bundle(bundle, context["goal"], context["event_type"])
            for bundle in parsed.get("candidate_bundles", [])
            if isinstance(bundle, dict)
        ]

    bundles = [
        make_bundle(
            "conservative_safety_bundle",
            context,
            [
                create_candidate_action("lighting_adjustment", "unoccupied_zones", "Conservatively dim unoccupied lights.", {"lighting_level_percent": 35}, "fallback", 0.8),
                create_candidate_action("hvac_setpoint_adjustment", "unoccupied_zones", "Use mild unoccupied HVAC setback.", {"cooling_setpoint_c": 25}, "fallback", 0.7),
                create_candidate_action("ventilation_adjustment", "unoccupied_zones", "Preserve IAQ with moderate unoccupied ventilation.", {"ventilation_percent": 50}, "fallback", 0.68),
            ],
            {"energy_saved_percent": 2.0, "comfort_impact": "neutral"},
        ),
        make_bundle(
            "balanced_efficiency_bundle",
            context,
            [
                create_candidate_action("lighting_adjustment", "unoccupied_zones", "Reduce unoccupied lighting.", {"lighting_level_percent": 25}, "fallback", 0.82),
                create_candidate_action("hvac_setpoint_adjustment", "unoccupied_zones", "Relax unoccupied cooling setpoint.", {"cooling_setpoint_c": 26}, "fallback", 0.74),
                create_candidate_action("ventilation_adjustment", "unoccupied_zones", "Reduce ventilation within safe candidate bounds.", {"ventilation_percent": 40}, "fallback", 0.7),
            ],
            {"energy_saved_percent": 4.0, "comfort_impact": "neutral"},
        ),
    ]

    if "carbon" in context["goal"]:
        bundles.append(
            make_bundle(
                "carbon_shift_bundle",
                context,
                [create_candidate_action("carbon_schedule_shift", "whole_building", "Shift flexible loads to lower-carbon windows.", {"comfort_guard_enabled": True}, "fallback", 0.78)],
                {"carbon_reduced_percent": 6.0},
            )
        )

    if context.get("building_context", {}).get("comfort", {}).get("status") in {"Warning", "Unsafe"}:
        bundles.append(
            make_bundle(
                "comfort_preserving_mode",
                context,
                [create_candidate_action("strategy_mode", "occupied_zones", "Preserve comfort and avoid risky direct changes.", {"comfort_guard_enabled": True}, "fallback", 0.85)],
                {"comfort_impact": "positive"},
            )
        )

    return bundles


def validate_generated_bundles(bundles: list[ActionBundle], context: dict | None = None) -> dict:
    valid_bundles = []
    invalid_bundles = []
    validation_results = []
    for bundle in bundles:
        result = validate_action_bundle(bundle)
        result_dict = to_dict(result)
        bundle_dict = to_dict(bundle)
        analysis = (context or {}).get("extra_context", {}).get("request_analysis", {})
        semantic_violations = bundle_semantic_violations(bundle_dict, analysis) if analysis else []
        result_dict["semantic_valid"] = not semantic_violations
        result_dict["semantic_violations"] = semantic_violations
        result_dict["valid"] = bool(result.valid and not semantic_violations)
        validation_results.append(result_dict)
        record_candidate_bundle_to_kg(bundle_dict, result_dict)
        if result.valid and not semantic_violations:
            valid_bundles.append(bundle_dict)
        else:
            invalid_bundles.append(bundle_dict)
    return {"valid_bundles": valid_bundles, "invalid_bundles": invalid_bundles, "validation_results": validation_results}


def deduplicate_valid_bundles(validation: dict) -> dict:
    unique = []
    seen = set()
    for bundle in validation.get("valid_bundles", []):
        signature = json.dumps(
            [
                {
                    "type": action.get("action_type"),
                    "target": action.get("target"),
                    "parameters": action.get("parameters", {}),
                }
                for action in bundle.get("actions", [])
            ],
            sort_keys=True,
        )
        if signature not in seen:
            seen.add(signature)
            unique.append(bundle)
    validation["valid_bundles"] = unique
    return validation


def numeric_distance(left: dict, right: dict) -> float:
    distance = 0.0
    keys = set(left) | set(right)
    for key in keys:
        left_value = left.get(key)
        right_value = right.get(key)
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            distance += abs(float(left_value) - float(right_value))
        elif left_value != right_value:
            distance += 1.0
    return distance


def bundle_distance(left: dict, right: dict) -> float:
    left_actions = sorted(left.get("actions", []), key=lambda action: action.get("action_type", ""))
    right_actions = sorted(right.get("actions", []), key=lambda action: action.get("action_type", ""))
    distance = abs(len(left_actions) - len(right_actions)) * 2.0
    for left_action, right_action in zip(left_actions, right_actions):
        if left_action.get("action_type") != right_action.get("action_type"):
            distance += 4.0
        if left_action.get("target") != right_action.get("target"):
            distance += 2.0
        distance += numeric_distance(left_action.get("parameters", {}), right_action.get("parameters", {}))
    return distance


def select_materially_distinct_bundles(bundles: list[dict], max_bundles: int, min_distance: float = 3.0) -> list[dict]:
    selected: list[dict] = []
    for bundle in bundles:
        if not selected or all(bundle_distance(bundle, existing) >= min_distance for existing in selected):
            selected.append(bundle)
        if len(selected) >= max_bundles:
            return selected

    for bundle in bundles:
        if bundle not in selected:
            selected.append(bundle)
        if len(selected) >= max_bundles:
            break
    return selected


def action_variant(action: dict, profile: str) -> dict:
    variant = json.loads(json.dumps(action))
    parameters = variant.setdefault("parameters", {})
    action_type = variant.get("action_type")

    if action_type == "hvac_setpoint_adjustment" and "cooling_setpoint_c" in parameters:
        current = float(parameters.get("cooling_setpoint_c") or 24)
        if profile == "conservative":
            parameters["cooling_setpoint_c"] = max(23, min(26, round(current + 1)))
            variant["description"] = "Use a conservative occupied cooling adjustment within safe comfort limits."
        elif profile == "assertive":
            parameters["cooling_setpoint_c"] = max(23, min(26, round(current - 1)))
            variant["description"] = "Use a stronger occupied cooling adjustment within safe comfort limits."
    elif action_type == "ventilation_adjustment":
        current = float(parameters.get("ventilation_multiplier") or 1.2)
        if profile == "conservative":
            parameters["ventilation_multiplier"] = max(1.1, min(1.5, round(current - 0.1, 2)))
            variant["description"] = "Increase fresh air moderately while watching energy use."
        elif profile == "assertive":
            parameters["ventilation_multiplier"] = max(1.1, min(1.5, round(current + 0.15, 2)))
            variant["description"] = "Increase fresh air more aggressively to recover IAQ faster."
        parameters.pop("ventilation_percent", None)
    elif action_type == "lighting_adjustment" and "lighting_level_percent" in parameters:
        current = float(parameters.get("lighting_level_percent") or 65)
        if profile == "conservative":
            parameters["lighting_level_percent"] = max(35, min(100, round(current + 10)))
            variant["description"] = "Keep occupied lighting brighter while improving usability."
        elif profile == "assertive":
            parameters["lighting_level_percent"] = max(35, min(100, round(current - 10)))
            variant["description"] = "Use the lowest occupied-safe lighting level requested."

    variant["confidence"] = safe_confidence(float(variant.get("confidence") or 0.7) - (0.03 if profile == "assertive" else 0.0))
    return variant


def create_semantic_variant_bundle(base_bundle: dict, context: dict, profile: str, index: int) -> ActionBundle:
    profile_labels = {
        "conservative": "comfort_guarded",
        "balanced": "balanced",
        "assertive": "faster_recovery",
    }
    actions = [
        action_variant(action, profile) if profile != "balanced" else json.loads(json.dumps(action))
        for action in base_bundle.get("actions", [])
    ]
    if context.get("extra_context", {}).get("request_analysis", {}).get("occupancy") == "unoccupied":
        next_meeting_minutes = context.get("extra_context", {}).get("request_analysis", {}).get("next_meeting_minutes")
        empty_room_values = {
            "conservative": {"lighting": 35, "cooling": 27, "ventilation": 50},
            "balanced": {"lighting": 25, "cooling": 28, "ventilation": 40},
            "assertive": {"lighting": 15, "cooling": 29, "ventilation": 30},
        }.get(profile, {"lighting": 25, "cooling": 28, "ventilation": 40})
        for action in actions:
            action["target"] = "unoccupied_zones"
            parameters = action.setdefault("parameters", {})
            if action.get("action_type") == "lighting_adjustment":
                parameters["lighting_level_percent"] = empty_room_values["lighting"]
            elif action.get("action_type") == "hvac_setpoint_adjustment":
                parameters["cooling_setpoint_c"] = empty_room_values["cooling"]
                parameters["applies_to_occupied_zones"] = False
            elif action.get("action_type") == "ventilation_adjustment":
                parameters.pop("ventilation_multiplier", None)
                parameters["ventilation_percent"] = empty_room_values["ventilation"]
            elif action.get("action_type") == "preconditioning_schedule" and next_meeting_minutes is not None:
                parameters["next_meeting_minutes"] = int(next_meeting_minutes)
    raw_bundle = {
        "bundle_name": f"{profile_labels.get(profile, profile)}_plan_{index}",
        "goal": context["goal"],
        "event_type": context["event_type"],
        "actions": actions,
        "rationale": (
            "Generated by the diversity controller from the LLM plan so EnergyPlus can compare "
            f"a {profile_labels.get(profile, profile).replace('_', ' ')} version of the same requested outcome."
        ),
        "constraints": context["constraints"],
        "expected_outcome": base_bundle.get("expected_outcome", {}),
        "created_by": "llm_plan_diversity_controller",
        "requires_simulation": True,
        "fallback_used": False,
    }
    return normalize_llm_bundle(raw_bundle, context["goal"], context["event_type"])


def diversify_valid_bundles(validation: dict, context: dict, max_bundles: int) -> dict:
    valid = validation.get("valid_bundles", [])
    if not valid:
        return validation

    distinct = select_materially_distinct_bundles(valid, max_bundles)
    analysis = context.get("extra_context", {}).get("request_analysis", {})
    needs_diversity = (
        bool(analysis.get("multi_objective"))
        or len(analysis.get("issues", [])) > 1
        or analysis.get("occupancy") == "unoccupied"
    )
    if len(distinct) >= min(3, max_bundles) or not needs_diversity:
        validation["valid_bundles"] = distinct
        return validation

    augmented = [normalize_llm_bundle(bundle, context["goal"], context["event_type"]) for bundle in distinct]
    base = distinct[0]
    for index, profile in enumerate(["conservative", "balanced", "assertive"], start=1):
        if len(augmented) >= min(3, max_bundles):
            break
        augmented.append(create_semantic_variant_bundle(base, context, profile, index))

    diversified = deduplicate_valid_bundles(validate_generated_bundles(augmented, context))
    diversified["valid_bundles"] = select_materially_distinct_bundles(
        diversified.get("valid_bundles", []),
        max_bundles,
        min_distance=2.0,
    )
    diversified["diversity_controller_applied"] = True
    return diversified


def generate_candidate_action_bundles(goal: str, event_type: str = "operator_request", extra_context: dict | None = None, max_bundles: int = 5) -> dict:
    context = build_candidate_generation_context(goal, event_type, extra_context)
    prompt = build_candidate_generation_prompt(context)
    try:
        llm_result = call_llm(prompt, context)
    except Exception as exc:
        llm_result = {
            "success": False,
            "mode": "unknown",
            "raw_text": "",
            "selected_provider": None,
            "attempted_providers": [],
            "fallback_used": True,
            "error": "LLM call failed; deterministic fallback bundles were used.",
            "error_summary": str(exc),
            "model": None,
            "latency_ms": 0,
            "dropped_actions": [],
            "dropped_bundles": [],
            "normalized_bundle_count": 0,
            "raw_bundle_count": 0,
        }
    parsed = extract_json_from_llm_text(llm_result.get("raw_text", ""))
    raw_bundles = parsed.get("candidate_bundles", [])[:max_bundles]
    bundles = []
    normalize_errors = []
    for raw_bundle in raw_bundles:
        if not isinstance(raw_bundle, dict):
            continue
        try:
            bundles.append(normalize_llm_bundle(raw_bundle, goal, event_type))
        except (TypeError, ValueError) as exc:
            normalize_errors.append(str(exc))
    bundles = repair_empty_room_bundles(bundles, context)
    bundles.extend(compose_complete_llm_bundles(bundles, context, max_bundles))
    validation = diversify_valid_bundles(
        deduplicate_valid_bundles(validate_generated_bundles(bundles, context)),
        context,
        max_bundles,
    )
    semantic_retry_applied = False
    initial_semantic_violations = [
        violation
        for result in validation["validation_results"]
        for violation in result.get("semantic_violations", [])
    ]

    if not validation["valid_bundles"] and bundles and initial_semantic_violations:
        semantic_retry_applied = True
        retry_context = {
            **context,
            "extra_context": {
                **context.get("extra_context", {}),
                "semantic_rejection_feedback": list(dict.fromkeys(initial_semantic_violations)),
                "retry_instruction": "Regenerate every candidate and correct every semantic contradiction listed here.",
            },
        }
        try:
            retry_result = call_llm(build_candidate_generation_prompt(retry_context), retry_context)
            retry_parsed = extract_json_from_llm_text(retry_result.get("raw_text", ""))
            retry_bundles = []
            retry_errors = []
            for raw_bundle in retry_parsed.get("candidate_bundles", [])[:max_bundles]:
                if not isinstance(raw_bundle, dict):
                    continue
                try:
                    retry_bundles.append(normalize_llm_bundle(raw_bundle, goal, event_type))
                except (TypeError, ValueError) as exc:
                    retry_errors.append(str(exc))
            retry_bundles = repair_empty_room_bundles(retry_bundles, retry_context)
            retry_bundles.extend(compose_complete_llm_bundles(retry_bundles, retry_context, max_bundles))
            retry_validation = diversify_valid_bundles(
                deduplicate_valid_bundles(validate_generated_bundles(retry_bundles, retry_context)),
                retry_context,
                max_bundles,
            )
            if retry_validation["valid_bundles"]:
                llm_result = retry_result
                parsed = retry_parsed
                bundles = retry_bundles
                normalize_errors.extend(retry_errors)
                validation = retry_validation
        except Exception as exc:
            normalize_errors.append(f"Semantic retry failed: {exc}")

    targeted_generation_applied = False
    targeted_generation_traces = []
    needs_candidate_diversity = (
        len(validation["valid_bundles"]) < 2
        and bool(context.get("extra_context", {}).get("request_analysis", {}).get("multi_objective"))
    )
    if needs_candidate_diversity:
        diversity_limit = min(max_bundles, 3)
        full_analysis = context.get("extra_context", {}).get("request_analysis", {})
        requirement_by_issue = {
            "high_temperature": "Cool the occupied room; do not raise or relax its cooling setpoint.",
            "low_temperature": "Warm the occupied room without degrading comfort.",
            "poor_air_quality": "Increase fresh-air ventilation; do not reduce ventilation.",
            "insufficient_lighting": "Increase usable lighting; do not dim the lights.",
            "excessive_lighting": "Reduce lighting to a usable occupied level.",
        }
        targeted_bundles = []
        targeted_all_real = True
        for issue in full_analysis.get("issues", []):
            targeted_generation_applied = True
            targeted_analysis = {
                **full_analysis,
                "issues": [issue],
                "requirements": [
                    "Treat the affected space as occupied; never target unoccupied zones."
                ] if full_analysis.get("occupancy") == "occupied" else [],
                "multi_objective": False,
            }
            if issue in requirement_by_issue:
                targeted_analysis["requirements"].append(requirement_by_issue[issue])
            targeted_context = {
                **context,
                "extra_context": {
                    **context.get("extra_context", {}),
                    "request_analysis": targeted_analysis,
                    "required_outcomes": targeted_analysis["requirements"],
                    "targeted_issue": issue,
                    "retry_instruction": "Generate at least two distinct safe candidate actions for this one issue only, using different reasonable parameter values.",
                },
            }
            try:
                targeted_result = call_llm(build_candidate_generation_prompt(targeted_context), targeted_context)
                targeted_parsed = extract_json_from_llm_text(targeted_result.get("raw_text", ""))
                targeted_generation_traces.append({
                    "issue": issue,
                    "provider": targeted_result.get("selected_provider"),
                    "fallbackUsed": bool(targeted_result.get("fallback_used", False)),
                    "bundleCount": len(targeted_parsed.get("candidate_bundles", [])),
                })
                targeted_all_real = targeted_all_real and not bool(targeted_result.get("fallback_used", False))
                for raw_bundle in targeted_parsed.get("candidate_bundles", [])[:2]:
                    if isinstance(raw_bundle, dict):
                        targeted_bundles.append(normalize_llm_bundle(raw_bundle, goal, event_type))
            except Exception as exc:
                targeted_all_real = False
                normalize_errors.append(f"Targeted generation for {issue} failed: {exc}")

        if targeted_bundles and targeted_all_real:
            targeted_composed = compose_complete_llm_bundles(targeted_bundles, context, diversity_limit)
            existing_valid = [
                normalize_llm_bundle(bundle, goal, event_type)
                for bundle in validation["valid_bundles"]
            ]
            combined_pool = []
            seen_combinations = set()
            for bundle in existing_valid + targeted_composed:
                bundle_dict = to_dict(bundle)
                signature = json.dumps(
                    [
                        {
                            "type": action.get("action_type"),
                            "target": action.get("target"),
                            "parameters": action.get("parameters", {}),
                        }
                        for action in bundle_dict.get("actions", [])
                    ],
                    sort_keys=True,
                )
                if signature not in seen_combinations:
                    seen_combinations.add(signature)
                    combined_pool.append(bundle)
                if len(combined_pool) >= diversity_limit:
                    break
            targeted_validation = diversify_valid_bundles(
                deduplicate_valid_bundles(validate_generated_bundles(combined_pool, context)),
                context,
                max_bundles,
            )
            if targeted_validation["valid_bundles"]:
                validation = targeted_validation
                llm_result = {
                    **llm_result,
                    "fallback_used": False,
                    "selected_provider": targeted_generation_traces[0].get("provider") if targeted_generation_traces else llm_result.get("selected_provider"),
                }
    used_fallback = False

    if not validation["valid_bundles"]:
        used_fallback = True
        fallback_bundles = generate_fallback_candidate_bundles(context)[:max_bundles]
        validation = validate_generated_bundles(fallback_bundles, context)

    building = context["building_context"]
    knowledge = context["knowledge_context"]
    experience_retrieval = context.get("experience_retrieval", {})
    recommendation = experience_retrieval.get("historical_recommendation") or {}
    return {
        "goal": goal,
        "event_type": event_type,
        "llm_result": {
            "success": llm_result.get("success", False),
            "mode": llm_result.get("mode", ""),
            "selected_provider": llm_result.get("selected_provider"),
            "attempted_providers": llm_result.get("attempted_providers", []),
            "fallback_used": bool(llm_result.get("fallback_used")) or used_fallback,
            "used_fallback": bool(llm_result.get("fallback_used")) or used_fallback,
            "error": llm_result.get("error") or parsed.get("parse_error"),
            "error_summary": llm_result.get("error_summary") or "; ".join(normalize_errors) or None,
            "model": llm_result.get("model"),
            "latency_ms": llm_result.get("latency_ms"),
            "schema_repair_applied": bool(llm_result.get("schema_repair_applied")),
            "repair_notes": llm_result.get("repair_notes", []),
            "provider_timeout_seconds": llm_result.get("provider_timeout_seconds"),
            "configured_provider_timeout_seconds": llm_result.get("configured_provider_timeout_seconds", {}),
            "retry_count": llm_result.get("retry_count", 0),
            "semantic_retry_applied": semantic_retry_applied,
            "initial_semantic_violations": list(dict.fromkeys(initial_semantic_violations)),
            "targeted_generation_applied": targeted_generation_applied,
            "targeted_generation_traces": targeted_generation_traces,
            "diversity_controller_applied": bool(validation.get("diversity_controller_applied", False)),
            "timed_out": bool(llm_result.get("timed_out")),
            "dropped_actions": llm_result.get("dropped_actions", []),
            "dropped_bundles": llm_result.get("dropped_bundles", []),
            "normalized_bundle_count": llm_result.get("normalized_bundle_count", 0),
            "raw_bundle_count": llm_result.get("raw_bundle_count", 0),
        },
        "context_summary": {
            "comfort_status": building.get("comfort", {}).get("status", "Safe"),
            "anomaly_count": building.get("anomalies", {}).get("anomaly_count", 0),
            "overall_score": building.get("score", {}).get("overall", 0),
            "knowledge_matches": len(knowledge.get("matched_conditions", [])),
            "similar_experiences_found": experience_retrieval.get("similar_experiences_found", 0),
        },
        "experience_graph": {
            "retrieval_used": True,
            "similar_experiences_found": experience_retrieval.get("similar_experiences_found", 0),
            "preferred_plan": recommendation.get("preferred_plan"),
            "average_reward": recommendation.get("average_reward"),
            "success_rate": recommendation.get("success_rate"),
            "actions_to_prefer": recommendation.get("actions_to_prefer", []),
            "actions_to_avoid": recommendation.get("actions_to_avoid", []),
            "message": experience_retrieval.get("message"),
        },
        "experience_retrieval": experience_retrieval,
        "llm_experience_context": context.get("experience_context_for_llm", ""),
        "candidate_bundles": validation["valid_bundles"],
        "invalid_bundles": validation["invalid_bundles"],
        "validation_results": validation["validation_results"],
        "guardrails": GUARDRAILS,
    }
