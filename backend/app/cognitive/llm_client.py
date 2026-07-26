import copy
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request

from backend.app.cognitive.action_bundle_schema import ALLOWED_ACTION_TYPES
from backend.app.cognitive.provider_schema_normalizer import (
    CANONICAL_ACTION_TYPES,
    normalize_llm_candidate_response,
)


ALLOWED_LLM_MODES = {"mock", "ollama", "openrouter", "auto", "disabled"}
LLM_PROVIDERS = {"ollama", "openrouter", "mock"}
DEFAULT_PROVIDER_PRIORITY = ["ollama", "openrouter", "mock"]
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 90
DEFAULT_OPENROUTER_TIMEOUT_SECONDS = 60
DEFAULT_LLM_TOTAL_TIMEOUT_SECONDS = 140


def get_llm_mode() -> str:
    mode = os.environ.get("FORGEHIVE_LLM_MODE", "mock").lower().strip()
    return mode if mode in ALLOWED_LLM_MODES else "mock"


def get_provider_priority() -> list[str]:
    raw_priority = os.environ.get("FORGEHIVE_LLM_PROVIDER_PRIORITY", "ollama,openrouter,mock")
    providers = [provider.strip().lower() for provider in raw_priority.split(",")]
    return [provider for provider in providers if provider in LLM_PROVIDERS]


def get_positive_timeout_seconds(env_name: str, default_value: int) -> float:
    raw_value = os.environ.get(env_name, "").strip()
    if not raw_value:
        return float(default_value)
    try:
        timeout_seconds = float(raw_value)
    except ValueError:
        return float(default_value)
    return timeout_seconds if timeout_seconds > 0 else float(default_value)


def get_ollama_timeout_seconds() -> float:
    return get_positive_timeout_seconds("FORGEHIVE_OLLAMA_TIMEOUT_SECONDS", DEFAULT_OLLAMA_TIMEOUT_SECONDS)


def get_openrouter_timeout_seconds() -> float:
    return get_positive_timeout_seconds("FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS", DEFAULT_OPENROUTER_TIMEOUT_SECONDS)


def get_llm_total_timeout_seconds() -> float:
    return get_positive_timeout_seconds("FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS", DEFAULT_LLM_TOTAL_TIMEOUT_SECONDS)


def provider_timeout_seconds(provider: str) -> float:
    if provider == "ollama":
        return get_ollama_timeout_seconds()
    if provider == "openrouter":
        return get_openrouter_timeout_seconds()
    return 0.0


def timeout_config_snapshot() -> dict:
    return {
        "ollama": get_ollama_timeout_seconds(),
        "openrouter": get_openrouter_timeout_seconds(),
        "total": get_llm_total_timeout_seconds(),
    }


def build_llm_system_prompt() -> str:
    return (
        "You are ForgeHive Cognitive Building Operator. You generate candidate "
        "action bundles only. You do not execute actions. You must output strict "
        "JSON. Every bundle must include multiple safe actions when appropriate. "
        "Candidate bundles must later be validated, safety-checked, simulated in "
        "EnergyPlus, ranked by RL, and executed only in Layer 5. Avoid unsafe "
        "values. Respect comfort, IAQ, occupancy, carbon, and anomaly constraints. "
        "If uncertain, choose conservative actions."
    )


def build_llm_schema_instructions() -> str:
    compact_example = {
        "candidate_bundles": [
            {
                "bundle_name": "request_specific_candidate",
                "goal": "operator_request_goal",
                "event_type": "operator_request_event",
                "actions": [
                    {
                        "action_type": "strategy_mode",
                        "target": "affected_zones",
                        "description": "Schema example only; derive the real action from the request.",
                        "parameters": {"mode": "request_specific_mode"},
                        "source": "llm_generated",
                        "confidence": 0.75,
                    }
                ],
                "rationale": "Address the operator request while preserving safety.",
                "constraints": ["Layer 4 cannot execute actions."],
                "expected_outcome": {"comfort_impact": "neutral"},
                "created_by": "llm_candidate_generator",
                "requires_simulation": True,
                "fallback_used": False,
            }
        ]
    }
    return (
        "Return only JSON. No markdown. No markdown fences. No backticks. No explanation. "
        "The top-level object must contain candidate_bundles. candidate_bundles must be a non-empty list. "
        "Each bundle must contain bundle_name, goal, event_type, actions, rationale, constraints, "
        "expected_outcome, created_by, requires_simulation, and fallback_used. "
        "expected_outcome must always be an object. constraints must always be a list. "
        "actions must be non-empty. Each action must contain action_type, target, description, "
        "parameters, source, and confidence. Use only these action_type values: "
        f"{', '.join(sorted(CANONICAL_ACTION_TYPES))}. "
        "Layer 4 cannot execute actions. Candidate bundles are only proposals for Layer 5 simulation. "
        "Layer 4 must not call EnergyPlus. Compact valid example: "
        f"{json.dumps(compact_example, separators=(',', ':'))}"
    )


def build_ollama_prompt(prompt: str) -> str:
    return f"{build_llm_system_prompt()}\n\n{build_llm_schema_instructions()}\n\nUser request:\n{prompt}"


def make_bundle(
    name: str,
    goal: str,
    event_type: str,
    actions: list[dict],
    rationale: str,
    constraints: list[str],
    expected_outcome: dict,
    fallback_used: bool = False,
) -> dict:
    return {
        "bundle_name": name,
        "goal": goal,
        "event_type": event_type,
        "actions": actions,
        "rationale": rationale,
        "constraints": constraints,
        "expected_outcome": expected_outcome,
        "created_by": "mock_llm_candidate_generator",
        "requires_simulation": True,
        "fallback_used": fallback_used,
    }


def make_action(
    action_type: str,
    target: str,
    description: str,
    parameters: dict,
    confidence: float,
) -> dict:
    return {
        "action_type": action_type,
        "target": target,
        "description": description,
        "parameters": parameters,
        "source": "llm_generated",
        "confidence": confidence,
    }


def call_mock_llm(prompt: str, context: dict | None = None) -> str:
    context = context or {}
    goal = context.get("goal", "balanced_optimization")
    event_type = context.get("event_type", "operator_request")
    extra = context.get("extra_context", {}) or {}
    building = context.get("building_context", {}) or {}
    comfort_status = building.get("comfort", {}).get("status", "Safe")
    anomalies = building.get("anomalies", {}).get("anomalies", [])
    anomaly_types = {anomaly.get("type") for anomaly in anomalies}
    next_meeting_minutes = int(extra.get("next_meeting_minutes", 60))
    constraints = context.get("constraints", [])
    request_analysis = extra.get("request_analysis", {}) or {}
    request_issues = set(request_analysis.get("issues", []))
    if request_issues:
        target = "occupied_zones" if request_analysis.get("occupancy") == "occupied" else "affected_zones"

        def request_actions(conservative: bool) -> list[dict]:
            actions = []
            if "high_temperature" in request_issues:
                actions.append(make_action(
                    "hvac_setpoint_adjustment",
                    target,
                    "Increase cooling to address the reported high temperature.",
                    {"cooling_setpoint_c": 24 if conservative else 23, "applies_to_occupied_zones": target == "occupied_zones"},
                    0.82,
                ))
            if "low_temperature" in request_issues:
                actions.append(make_action("strategy_mode", target, "Use occupied comfort heating mode.", {"mode": "comfort_mode"}, 0.78))
            if "poor_air_quality" in request_issues:
                actions.append(make_action(
                    "ventilation_adjustment",
                    target,
                    "Increase fresh-air ventilation to address the reported suffocating air.",
                    {"ventilation_multiplier": 1.15 if conservative else 1.3, "applies_to_occupied_zones": target == "occupied_zones"},
                    0.86,
                ))
            if "insufficient_lighting" in request_issues:
                actions.append(make_action(
                    "lighting_adjustment",
                    target,
                    "Increase usable lighting for clear visibility.",
                    {"lighting_level_percent": 65 if conservative else 80},
                    0.84,
                ))
            if "excessive_lighting" in request_issues:
                actions.append(make_action(
                    "lighting_adjustment",
                    target,
                    "Reduce excessive lighting while preserving visibility.",
                    {"lighting_level_percent": 60 if conservative else 50},
                    0.82,
                ))
            return actions

        aligned_bundles = [
            make_bundle(
                "request_aligned_conservative_bundle",
                goal,
                event_type,
                request_actions(True),
                "Conservative fallback aligned with every detected operator requirement.",
                constraints,
                {"comfort_impact": "positive"},
                fallback_used=True,
            ),
            make_bundle(
                "request_aligned_balanced_bundle",
                goal,
                event_type,
                request_actions(False),
                "Balanced fallback aligned with every detected operator requirement.",
                constraints,
                {"comfort_impact": "positive"},
                fallback_used=True,
            ),
        ]
        return json.dumps({"candidate_bundles": aligned_bundles}, indent=2)

    mild_cooling_setpoint = 25 if next_meeting_minutes <= 30 else 26
    stronger_cooling_setpoint = 26 if next_meeting_minutes <= 30 else 28
    mild_ventilation = 50 if "poor_iaq" in anomaly_types or "elevated_co2" in anomaly_types else 40
    stronger_ventilation = 50 if "poor_iaq" in anomaly_types or "elevated_co2" in anomaly_types else 30

    bundles = [
        make_bundle(
            "conservative_safety_bundle",
            goal,
            event_type,
            [
                make_action("lighting_adjustment", "unoccupied_zones", "Dim lights conservatively in empty rooms.", {"lighting_level_percent": 35}, 0.82),
                make_action("hvac_setpoint_adjustment", "unoccupied_zones", "Apply mild unoccupied cooling setback.", {"cooling_setpoint_c": mild_cooling_setpoint}, 0.74),
                make_action("ventilation_adjustment", "unoccupied_zones", "Use moderate ventilation reduction while preserving IAQ.", {"ventilation_percent": mild_ventilation}, 0.70),
            ],
            "Conservative bundle prioritizes safety while reducing waste.",
            constraints,
            {"energy_saved_percent": 2.5, "comfort_impact": "neutral"},
        ),
        make_bundle(
            "balanced_efficiency_bundle",
            goal,
            event_type,
            [
                make_action("lighting_adjustment", "unoccupied_zones", "Reduce lighting in empty rooms.", {"lighting_level_percent": 25}, 0.86),
                make_action("hvac_setpoint_adjustment", "unoccupied_zones", "Relax HVAC setpoint for longer empty-room window.", {"cooling_setpoint_c": stronger_cooling_setpoint}, 0.78),
                make_action("ventilation_adjustment", "unoccupied_zones", "Reduce ventilation only within safe candidate bounds.", {"ventilation_percent": stronger_ventilation}, 0.72),
            ],
            "Balanced bundle combines lighting, HVAC, and ventilation candidates for simulation.",
            constraints,
            {"energy_saved_percent": 4.5, "comfort_impact": "neutral"},
        ),
        make_bundle(
            "aggressive_but_safe_bundle",
            goal,
            event_type,
            [
                make_action("lighting_adjustment", "unoccupied_zones", "Dim lighting more strongly in confirmed empty rooms.", {"lighting_level_percent": 15}, 0.68),
                make_action("hvac_setpoint_adjustment", "unoccupied_zones", "Use stronger unoccupied-only HVAC setback.", {"cooling_setpoint_c": 29}, 0.62),
                make_action("no_direct_control_change", "occupied_zones", "Keep occupied zones unchanged.", {}, 0.95),
            ],
            "Aggressive candidate remains unoccupied-only and must be simulated before execution.",
            constraints,
            {"energy_saved_percent": 6.0, "comfort_impact": "neutral"},
        ),
    ]

    if "carbon" in goal:
        bundles.append(
            make_bundle(
                "carbon_aware_shift_bundle",
                goal,
                event_type,
                [
                    make_action("carbon_schedule_shift", "whole_building", "Shift flexible loads away from high-carbon windows.", {"comfort_guard_enabled": True, "avoid_peak_carbon_window": True}, 0.82),
                    make_action("strategy_mode", "whole_building", "Enable carbon-aware operation with comfort guard.", {"mode": "carbon_aware_mode"}, 0.78),
                ],
                "Carbon goal benefits from schedule shifting rather than aggressive immediate control.",
                constraints,
                {"carbon_reduced_percent": 6.0, "comfort_impact": "neutral"},
            )
        )

    if "comfort" in goal or comfort_status in {"Warning", "Unsafe"}:
        bundles.append(
            make_bundle(
                "comfort_preserving_bundle",
                goal,
                event_type,
                [
                    make_action("strategy_mode", "occupied_zones", "Enable comfort-preserving mode.", {"comfort_guard_enabled": True}, 0.88),
                    make_action("no_direct_control_change", "occupied_zones", "Avoid direct occupied-zone changes until comfort is safe.", {}, 0.90),
                ],
                "Comfort preservation takes priority when comfort is requested or degraded.",
                constraints,
                {"comfort_impact": "positive"},
            )
        )

    if "poor_iaq" in anomaly_types or "elevated_co2" in anomaly_types:
        bundles.append(
            make_bundle(
                "iaq_recovery_bundle",
                goal,
                event_type,
                [
                    make_action("ventilation_adjustment", "occupied_zones", "Increase ventilation for elevated CO2.", {"ventilation_multiplier": 1.25}, 0.9),
                    make_action("strategy_mode", "whole_building", "Enable IAQ priority mode.", {"mode": "iaq_priority_mode"}, 0.84),
                ],
                "IAQ anomalies require ventilation improvement before efficiency actions.",
                constraints,
                {"comfort_impact": "positive", "iaq_impact": "improves"},
            )
        )

    return json.dumps({"candidate_bundles": bundles[:5]}, indent=2)


def strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    if cleaned.startswith("`") and cleaned.endswith("`"):
        cleaned = cleaned.strip("`").strip()
    return cleaned


def extract_first_json_value(text: str):
    cleaned = strip_markdown_fences(text or "")
    decoder = json.JSONDecoder()

    for index, character in enumerate(cleaned):
        if character not in "[{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, (dict, list)):
            return parsed

    return None


def extract_json_from_llm_text(text: str) -> dict:
    parsed = extract_first_json_value(text)
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        return {"candidate_bundles": parsed}

    return {"candidate_bundles": [], "parse_error": "No valid JSON object or array found in LLM text."}


def context_goal(context: dict | None) -> str:
    return (context or {}).get("goal", "balanced_optimization")


def context_event_type(context: dict | None) -> str:
    return (context or {}).get("event_type", "operator_request")


def default_target_for_context(context: dict | None) -> str:
    if context_event_type(context) == "empty_room_detected":
        return "unoccupied_zones"
    return "whole_building"


def describe_action_type(action_type: str) -> str:
    readable = str(action_type or "candidate action").replace("_", " ")
    return f"Candidate {readable} for simulation and safety review."


def action_like_fields_from_bundle(bundle: dict) -> dict | None:
    if "action_type" not in bundle:
        return None
    action = {}
    for field in ["action_type", "target", "description", "parameters", "action_value", "source", "confidence"]:
        if field in bundle:
            action[field] = bundle[field]
    return action


def normalize_provider_action(raw_action: dict, provider: str, context: dict | None, bundle_index: int, action_index: int, repair_notes: list[str]) -> dict:
    if not isinstance(raw_action, dict):
        raise ValueError(f"candidate_bundles[{bundle_index}].actions[{action_index}] must be an object.")

    action = copy.deepcopy(raw_action)
    action_type = action.get("action_type")
    if action_type not in ALLOWED_ACTION_TYPES:
        raise ValueError(f"candidate_bundles[{bundle_index}].actions[{action_index}].action_type is not allowed: {action_type}")

    if "target" not in action or not action.get("target"):
        action["target"] = default_target_for_context(context)
        repair_notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].target defaulted to {action['target']}.")

    if "description" not in action or not action.get("description"):
        action["description"] = describe_action_type(action_type)
        repair_notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].description defaulted.")

    parameters = action.get("parameters")
    if parameters is None:
        parameters = {}
        repair_notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].parameters defaulted to empty object.")
    elif not isinstance(parameters, dict):
        raise ValueError(f"candidate_bundles[{bundle_index}].actions[{action_index}].parameters must be an object.")

    if "action_value" in action:
        parameters = dict(parameters)
        parameters["value"] = action.pop("action_value")
        repair_notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].action_value moved into parameters.value.")

    action["parameters"] = parameters

    if "source" not in action or not action.get("source"):
        action["source"] = "llm_generated"
        repair_notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].source defaulted.")

    if "confidence" not in action or action.get("confidence") is None:
        action["confidence"] = 0.65
        repair_notes.append(f"candidate_bundles[{bundle_index}].actions[{action_index}].confidence defaulted to 0.65.")
    else:
        try:
            confidence = float(action.get("confidence"))
        except (TypeError, ValueError):
            raise ValueError(f"candidate_bundles[{bundle_index}].actions[{action_index}].confidence must be numeric.")
        if not 0 <= confidence <= 1:
            raise ValueError(f"candidate_bundles[{bundle_index}].actions[{action_index}].confidence must be between 0 and 1.")
        action["confidence"] = confidence

    return action


def normalize_provider_bundle(raw_bundle: dict, provider: str, context: dict | None, bundle_index: int, repair_notes: list[str]) -> dict:
    if not isinstance(raw_bundle, dict):
        raise ValueError(f"candidate_bundles[{bundle_index}] must be an object.")

    bundle = copy.deepcopy(raw_bundle)
    if "bundle_name" not in bundle and "bundle_id" in bundle:
        bundle["bundle_name"] = str(bundle["bundle_id"])
        repair_notes.append(f"candidate_bundles[{bundle_index}].bundle_id converted to bundle_name.")

    if "bundle_name" not in bundle or not isinstance(bundle.get("bundle_name"), str) or not bundle.get("bundle_name"):
        raise ValueError(f"candidate_bundles[{bundle_index}].bundle_name is missing.")

    if "goal" not in bundle or not bundle.get("goal"):
        bundle["goal"] = context_goal(context)
        repair_notes.append(f"candidate_bundles[{bundle_index}].goal defaulted from context.")

    if "event_type" not in bundle or not bundle.get("event_type"):
        bundle["event_type"] = context_event_type(context)
        repair_notes.append(f"candidate_bundles[{bundle_index}].event_type defaulted from context.")

    raw_actions = bundle.get("actions")
    if not isinstance(raw_actions, list) or len(raw_actions) == 0:
        recovered_action = action_like_fields_from_bundle(bundle)
        if not recovered_action:
            raise ValueError(f"candidate_bundles[{bundle_index}] must contain a non-empty actions list.")
        raw_actions = [recovered_action]
        bundle["actions"] = raw_actions
        repair_notes.append(f"candidate_bundles[{bundle_index}].actions recovered from bundle-level action fields.")

    bundle["actions"] = [
        normalize_provider_action(action, provider, context, bundle_index, action_index, repair_notes)
        for action_index, action in enumerate(raw_actions)
    ]

    if "rationale" not in bundle or not bundle.get("rationale"):
        bundle["rationale"] = "Generated candidate bundle for simulation and safety review."
        repair_notes.append(f"candidate_bundles[{bundle_index}].rationale defaulted.")

    if "constraints" not in bundle or bundle.get("constraints") is None:
        bundle["constraints"] = []
        repair_notes.append(f"candidate_bundles[{bundle_index}].constraints defaulted to empty list.")
    elif not isinstance(bundle.get("constraints"), list):
        raise ValueError(f"candidate_bundles[{bundle_index}].constraints must be a list.")

    if "expected_outcome" not in bundle or bundle.get("expected_outcome") is None:
        bundle["expected_outcome"] = {}
        repair_notes.append(f"candidate_bundles[{bundle_index}].expected_outcome defaulted to empty object.")
    elif not isinstance(bundle.get("expected_outcome"), dict):
        raise ValueError(f"candidate_bundles[{bundle_index}].expected_outcome must be an object.")

    if "created_by" not in bundle or not bundle.get("created_by"):
        bundle["created_by"] = f"{provider}_llm_candidate_generator"
        repair_notes.append(f"candidate_bundles[{bundle_index}].created_by defaulted.")

    if "requires_simulation" not in bundle or bundle.get("requires_simulation") is None:
        bundle["requires_simulation"] = True
        repair_notes.append(f"candidate_bundles[{bundle_index}].requires_simulation defaulted to true.")

    if "fallback_used" not in bundle or bundle.get("fallback_used") is None:
        bundle["fallback_used"] = False
        repair_notes.append(f"candidate_bundles[{bundle_index}].fallback_used defaulted to false.")

    return bundle


def repair_provider_candidate_bundles(raw_text: str, provider: str, context: dict | None = None) -> dict:
    parsed = extract_json_from_llm_text(raw_text)
    if parsed.get("parse_error"):
        raise ValueError(parsed["parse_error"])

    normalized = normalize_llm_candidate_response(
        parsed,
        provider,
        context_goal(context),
        context_event_type(context),
    )
    repaired = normalized["normalized_response"]
    if normalized["normalized_bundle_count"] == 0:
        raise ValueError(
            "No valid normalized candidate bundles remained. "
            f"repair_notes={normalized['repair_notes']} "
            f"dropped_actions={normalized['dropped_actions']} "
            f"dropped_bundles={normalized['dropped_bundles']}"
        )

    repaired_text = json.dumps(repaired, indent=2)
    valid, validation_error = parsed_response_has_candidate_bundles(repaired_text)
    if not valid:
        raise ValueError(validation_error)

    return {
        "payload": repaired,
        "raw_text": repaired_text,
        "schema_repair_applied": normalized["schema_repair_applied"],
        "repair_notes": normalized["repair_notes"],
        "dropped_actions": normalized["dropped_actions"],
        "dropped_bundles": normalized["dropped_bundles"],
        "normalized_bundle_count": normalized["normalized_bundle_count"],
        "raw_bundle_count": normalized["raw_bundle_count"],
    }


def parsed_response_has_candidate_bundles(raw_text: str) -> tuple[bool, str | None]:
    parsed = extract_json_from_llm_text(raw_text)
    if parsed.get("parse_error"):
        return False, parsed["parse_error"]
    candidate_bundles = parsed.get("candidate_bundles")
    if not isinstance(candidate_bundles, list) or len(candidate_bundles) == 0:
        return False, "Response did not contain a non-empty candidate_bundles list."
    for index, bundle in enumerate(candidate_bundles):
        if not isinstance(bundle, dict):
            return False, f"candidate_bundles[{index}] must be an object."
        if not isinstance(bundle.get("bundle_name", "candidate_bundle"), str):
            return False, f"candidate_bundles[{index}].bundle_name must be a string."
        actions = bundle.get("actions")
        if not isinstance(actions, list) or len(actions) == 0:
            return False, f"candidate_bundles[{index}] must contain a non-empty actions list."
        for action_index, action in enumerate(actions):
            if not isinstance(action, dict):
                return False, f"candidate_bundles[{index}].actions[{action_index}] must be an object."
            action_type = action.get("action_type")
            if action_type not in ALLOWED_ACTION_TYPES:
                return False, f"candidate_bundles[{index}].actions[{action_index}].action_type is not allowed: {action_type}"
            if "parameters" in action and not isinstance(action.get("parameters"), dict):
                return False, f"candidate_bundles[{index}].actions[{action_index}].parameters must be an object."
            if "confidence" in action:
                try:
                    confidence = float(action.get("confidence"))
                except (TypeError, ValueError):
                    return False, f"candidate_bundles[{index}].actions[{action_index}].confidence must be numeric."
                if not 0 <= confidence <= 1:
                    return False, f"candidate_bundles[{index}].actions[{action_index}].confidence must be between 0 and 1."
    return True, None


def call_ollama_llm(prompt: str, model: str | None = None, timeout_seconds: float | None = None) -> str:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    selected_model = model or os.environ.get("FORGEHIVE_OLLAMA_MODEL", "llama3.1:8b")
    request_timeout_seconds = timeout_seconds if timeout_seconds is not None else get_ollama_timeout_seconds()
    payload = json.dumps(
        {
            "model": selected_model,
            "prompt": build_ollama_prompt(prompt),
            "stream": False,
            "format": "json",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=request_timeout_seconds) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Ollama response JSON was not an object.")
    response_text = data.get("response", "")
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Ollama response did not contain text.")
    return response_text


def call_openrouter_llm(prompt: str, model: str | None = None, timeout_seconds: float | None = None) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key or api_key == "your_openrouter_key_here":
        raise ValueError("OPENROUTER_API_KEY is missing; skipped OpenRouter.")

    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    selected_model = model or os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
    request_timeout_seconds = timeout_seconds if timeout_seconds is not None else get_openrouter_timeout_seconds()
    payload = json.dumps(
        {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": f"{build_llm_system_prompt()}\n\n{build_llm_schema_instructions()}"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://forgehive.local",
            "X-Title": "ForgeHive",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=request_timeout_seconds) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("OpenRouter response JSON was not an object.")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("OpenRouter response did not contain choices.")
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    if not isinstance(content, str) or not content.strip():
        raise ValueError("OpenRouter response did not contain message content.")
    return content


def model_for_provider(provider: str) -> str:
    if provider == "ollama":
        return os.environ.get("FORGEHIVE_OLLAMA_MODEL", "llama3.1:8b")
    if provider == "openrouter":
        return os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
    return "mock"


def call_provider(provider: str, prompt: str, context: dict | None = None, timeout_seconds: float | None = None) -> str:
    if provider == "mock":
        return call_mock_llm(prompt, context)
    if provider == "ollama":
        return call_ollama_llm(prompt, timeout_seconds=timeout_seconds)
    if provider == "openrouter":
        return call_openrouter_llm(prompt, timeout_seconds=timeout_seconds)
    raise ValueError(f"Unsupported LLM provider: {provider}")


def is_timeout_exception(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, urllib.error.URLError) and "timed out" in str(getattr(exc, "reason", "")).lower():
        return True
    return "timed out" in str(exc).lower()


def providers_for_mode(mode: str) -> list[str]:
    if mode == "auto":
        priority = get_provider_priority()
        return priority or DEFAULT_PROVIDER_PRIORITY
    if mode in {"mock", "ollama", "openrouter"}:
        return [mode] if mode == "mock" else [mode, "mock"]
    return []


def build_disabled_llm_result(mode: str) -> dict:
    return {
        "success": False,
        "mode": mode,
        "raw_text": "",
        "error": "LLM mode is disabled. No provider was called and no action was executed.",
        "selected_provider": None,
        "attempted_providers": [],
        "fallback_used": False,
        "error_summary": "LLM mode is disabled. Candidate generation may use deterministic fallback bundles.",
        "model": None,
        "latency_ms": 0,
        "schema_repair_applied": False,
        "repair_notes": [],
        "provider_timeout_seconds": 0.0,
        "configured_provider_timeout_seconds": timeout_config_snapshot(),
        "retry_count": 0,
        "timed_out": False,
        "dropped_actions": [],
        "dropped_bundles": [],
        "normalized_bundle_count": 0,
        "raw_bundle_count": 0,
    }


def call_llm(prompt: str, context: dict | None = None) -> dict:
    mode = get_llm_mode()
    if mode == "disabled":
        return build_disabled_llm_result(mode)

    attempted_providers = []
    provider_errors = []
    retry_count = 0
    timed_out = False
    total_timeout_seconds = get_llm_total_timeout_seconds()
    started = time.perf_counter()

    for provider in providers_for_mode(mode):
        if time.perf_counter() - started >= total_timeout_seconds:
            provider_errors.append(f"total LLM timeout exceeded before {provider}.")
            break

        attempted_providers.append(provider)
        provider_started = time.perf_counter()
        selected_provider_timeout_seconds = provider_timeout_seconds(provider)
        max_attempts = 2 if provider == "ollama" else 1

        for attempt_index in range(max_attempts):
            try:
                raw_text = call_provider(provider, prompt, context, selected_provider_timeout_seconds)
                repair_result = repair_provider_candidate_bundles(raw_text, provider, context)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                return {
                    "success": True,
                    "mode": mode,
                    "raw_text": repair_result["raw_text"],
                    "error": None,
                    "selected_provider": provider,
                    "attempted_providers": attempted_providers,
                    "fallback_used": len(attempted_providers) > 1,
                    "error_summary": "; ".join(provider_errors) if provider_errors else None,
                    "model": model_for_provider(provider),
                    "latency_ms": latency_ms,
                    "provider_latency_ms": round((time.perf_counter() - provider_started) * 1000, 2),
                    "schema_repair_applied": repair_result["schema_repair_applied"],
                    "repair_notes": repair_result["repair_notes"],
                    "provider_timeout_seconds": selected_provider_timeout_seconds,
                    "configured_provider_timeout_seconds": timeout_config_snapshot(),
                    "retry_count": retry_count,
                    "timed_out": timed_out,
                    "dropped_actions": repair_result["dropped_actions"],
                    "dropped_bundles": repair_result["dropped_bundles"],
                    "normalized_bundle_count": repair_result["normalized_bundle_count"],
                    "raw_bundle_count": repair_result["raw_bundle_count"],
                }
            except Exception as exc:
                provider_timed_out = is_timeout_exception(exc)
                timed_out = timed_out or provider_timed_out
                if provider == "ollama" and provider_timed_out and attempt_index == 0:
                    retry_count += 1
                    provider_errors.append(
                        f"{provider}: timed out after {selected_provider_timeout_seconds:g}s; retrying once."
                    )
                    continue
                if provider_timed_out:
                    provider_errors.append(f"{provider}: timed out after {selected_provider_timeout_seconds:g}s.")
                else:
                    provider_errors.append(f"{provider}: {exc}")
                break

    fallback_text = call_mock_llm(prompt, context)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "success": True,
        "mode": mode,
        "raw_text": fallback_text,
        "error": "All configured providers failed; used mock fallback.",
        "selected_provider": "mock",
        "attempted_providers": attempted_providers + ([] if "mock" in attempted_providers else ["mock"]),
        "fallback_used": True,
        "error_summary": "; ".join(provider_errors),
        "model": "mock",
        "latency_ms": latency_ms,
        "schema_repair_applied": False,
        "repair_notes": [],
        "provider_timeout_seconds": 0.0,
        "configured_provider_timeout_seconds": timeout_config_snapshot(),
        "retry_count": retry_count,
        "timed_out": timed_out,
        "dropped_actions": [],
        "dropped_bundles": [],
        "normalized_bundle_count": 0,
        "raw_bundle_count": 0,
    }
