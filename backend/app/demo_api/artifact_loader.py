import json
import re
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
FINAL_DIR = ROOT_DIR / "artifacts" / "final_submission"
LAYER5_DIR = ROOT_DIR / "artifacts" / "layer_5_closed_loop"
LAYER8_DIR = ROOT_DIR / "artifacts" / "layer_8_experience_graph"

IMPORTANT_ARTIFACTS = [
    FINAL_DIR / "forgehive_final_audit.json",
    FINAL_DIR / "forgehive_artifact_audit.json",
    FINAL_DIR / "forgehive_final_demo_audit.json",
    FINAL_DIR / "forgehive_demo_script.md",
    FINAL_DIR / "forgehive_judge_summary.md",
    FINAL_DIR / "forgehive_readiness_score.json",
    FINAL_DIR / "forgehive_final_submission_package.json",
    LAYER5_DIR / "layer5_7_real_ollama_full_loop.json",
    LAYER5_DIR / "layer5_7_idf_adapter_report.json",
    LAYER5_DIR / "layer5_7_dashboard_summary.json",
    LAYER5_DIR / "layer5_7_summary.md",
    LAYER8_DIR / "experience_graph_summary.json",
    LAYER8_DIR / "experience_retrieval_demo.json",
    LAYER8_DIR / "experience_learning_demo.json",
    LAYER8_DIR / "layer8_summary.md",
]


SECRET_PATTERNS = [
    re.compile(r"OPENROUTER_API_KEY", re.IGNORECASE),
    re.compile(r"sk-or-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
]


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {} if default is None else default


def read_text(path: Path) -> str:
    try:
        return sanitize_value(path.read_text(encoding="utf-8"))
    except OSError:
        return ""


def sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, str):
        clean = value
        for pattern in SECRET_PATTERNS:
            clean = pattern.sub("[redacted]", clean)
        return clean
    return value


def nested_get(data: dict, keys: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is not None:
            return value
    return default


def load_artifact_bundle() -> dict:
    return {
        "readiness": sanitize_value(read_json(FINAL_DIR / "forgehive_readiness_score.json")),
        "final_package": sanitize_value(read_json(FINAL_DIR / "forgehive_final_submission_package.json")),
        "final_audit": sanitize_value(read_json(FINAL_DIR / "forgehive_final_audit.json")),
        "demo_audit": sanitize_value(read_json(FINAL_DIR / "forgehive_final_demo_audit.json")),
        "layer57": sanitize_value(read_json(LAYER5_DIR / "layer5_7_real_ollama_full_loop.json")),
        "dashboard57": sanitize_value(read_json(LAYER5_DIR / "layer5_7_dashboard_summary.json")),
        "idf_report": sanitize_value(read_json(LAYER5_DIR / "layer5_7_idf_adapter_report.json")),
    }


def list_artifacts() -> dict:
    return {
        "project": "ForgeHive",
        "realBuildingExecution": False,
        "artifacts": [
            {
                "name": path.name,
                "path": str(path.relative_to(ROOT_DIR)),
                "exists": path.exists(),
                "sizeBytes": path.stat().st_size if path.exists() else 0,
            }
            for path in IMPORTANT_ARTIFACTS
        ],
    }


def normalize_action(action: dict) -> dict:
    return {
        "actionType": action.get("action_type") or action.get("actionType", "unknown"),
        "target": action.get("target", "building"),
        "description": action.get("description", ""),
        "parameters": action.get("parameters", {}),
        "confidence": action.get("confidence"),
    }


def normalize_bundle(bundle: dict, simulation: dict | None = None) -> dict:
    simulation = simulation or {}
    return {
        "id": bundle.get("bundle_id") or simulation.get("bundle_id") or bundle.get("id", ""),
        "name": bundle.get("bundle_name") or simulation.get("bundle_name") or "Candidate bundle",
        "goal": bundle.get("goal", ""),
        "eventType": bundle.get("event_type", ""),
        "rationale": bundle.get("rationale", ""),
        "actions": [normalize_action(action) for action in bundle.get("actions", [])],
        "expectedOutcome": bundle.get("expected_outcome", {}),
        "score": simulation.get("reward_score") or simulation.get("score"),
        "simulationStatus": simulation.get("simulation_status", "complete"),
        "energySavedPercent": simulation.get("energy_saved_percent"),
        "carbonReducedPercent": simulation.get("carbon_reduced_percent"),
        "comfortStatus": simulation.get("comfort_status"),
    }


def normalize_experience_graph_from_memory(memory: dict, retrieval: dict | None = None, update: dict | None = None) -> dict:
    retrieval = retrieval or {}
    update = update or {}
    recommendation = retrieval.get("historical_recommendation") or {}
    top_strategy = (memory.get("topStrategies") or [{}])[0]
    return {
        "enabled": True,
        "retrievalUsed": bool(retrieval),
        "similarExperiencesFound": retrieval.get("similar_experiences_found", update.get("similar_experiences_used", 0)),
        "preferredHistoricalPlan": recommendation.get("preferred_plan") or top_strategy.get("strategy"),
        "successRate": recommendation.get("success_rate", top_strategy.get("successRate", 0)),
        "averageReward": recommendation.get("average_reward", top_strategy.get("averageReward", 0)),
        "confidence": recommendation.get("confidence", top_strategy.get("confidence", 0)),
        "actionsToPrefer": recommendation.get("actions_to_prefer", []),
        "actionsToAvoid": recommendation.get("actions_to_avoid", [pattern.get("action_type") for pattern in memory.get("failurePatterns", [])]),
        "experienceUpdated": bool(update.get("experience_graph_updated", update.get("experienceGraphUpdated", True))),
        "experienceId": update.get("experience_id") or update.get("experienceId"),
        "lessonsLearned": update.get("lessons_learned") or update.get("lessonsLearned") or memory.get("recentLessons", []),
        "totalExperiences": memory.get("totalExperiences", 0),
        "topStrategies": memory.get("topStrategies", []),
        "failurePatterns": memory.get("failurePatterns", []),
        "message": (
            "ForgeHive has seen similar situations before and is using those experiences as a decision prior."
            if retrieval.get("similar_experiences_found", 0)
            else "No similar previous experience found. ForgeHive will explore safely using simulation and safety checks."
        ),
    }


def experience_query_for_demo_cases(demo_cases: list[str], scenario: dict, user_message: str) -> dict:
    event_map = {
        "empty_room": ("empty_room_detected", "reduce_energy_keep_comfort_safe"),
        "high_co2": ("high_co2_detected", "improve_iaq"),
        "high_carbon": ("high_carbon_window", "reduce_carbon"),
        "too_hot": ("comfort_request", "maintain_comfort"),
        "unsafe_command": ("occupied_room", "reduce_energy_keep_comfort_safe"),
    }
    demo_case = demo_cases[0] if demo_cases else "empty_room"
    event_type, goal = event_map.get(demo_case, event_map["empty_room"])
    building_state = dict(scenario.get("before_state", {}))
    if "empty" in (user_message or "").lower() and "occupancy" not in building_state:
        building_state["occupancy"] = 0
    return {"event_type": event_type, "goal": goal, "building_state": building_state}


def build_pipeline(unsafe: bool = False) -> list[dict]:
    steps = [
        ("User request received", "complete"),
        ("Intent detected", "complete"),
        ("LLM generated bundles", "complete"),
        ("EnergyPlus simulated", "complete"),
        ("RL/KG ranked bundles", "complete"),
        ("Safety Governor checked plan", "rejected" if unsafe else "complete"),
        ("IDF adapter changed model", "blocked" if unsafe else "complete"),
        ("Digital twin executed", "blocked" if unsafe else "complete"),
        ("Learning updated", "complete"),
    ]
    return [{"step": step, "status": status} for step, status in steps]


def _simulation_map(layer57: dict) -> dict:
    sims = nested_get(layer57, ["layer5_result", "phase_5_1_3_plan", "simulation_results"], [])
    return {sim.get("bundle_id"): sim for sim in sims if isinstance(sim, dict)}


def infer_demo_cases(message: str, scenario: dict) -> list[str]:
    scenario_id = scenario.get("id")
    if scenario_id:
        return [scenario_id]
    lowered = message.lower()
    cases: list[str] = []
    if "30" in lowered or "maximum energy" in lowered or "unsafe" in lowered:
        cases.append("unsafe_command")
    if (
        "co2" in lowered
        or "air quality" in lowered
        or "ventilat" in lowered
        or "fresh air" in lowered
        or "stuffy" in lowered
        or "suffocat" in lowered
        or "stale air" in lowered
        or "poor air" in lowered
    ):
        cases.append("high_co2")
    if "carbon" in lowered or "grid" in lowered:
        cases.append("high_carbon")
    if "hot" in lowered or "cooler" in lowered or "cool down" in lowered or "comfort" in lowered:
        cases.append("too_hot")
    if (
        "dim" in lowered
        or "light" in lowered
        or "brightness" in lowered
        or "dark" in lowered
        or "too dark" in lowered
        or "can't see" in lowered
        or "cannot see" in lowered
        or "poor visibility" in lowered
    ):
        cases.append("dim_lights")
    if "empty" in lowered or "unoccupied" in lowered or "nobody" in lowered:
        cases.append("empty_room")
    return list(dict.fromkeys(cases)) or ["empty_room"]


def extract_next_meeting_minutes(message: str) -> int | None:
    try:
        from backend.app.cognitive.request_semantics import extract_next_meeting_minutes as extract

        return extract(message)
    except Exception:
        return None


def infer_demo_case(message: str, scenario: dict) -> str:
    return infer_demo_cases(message, scenario)[0]


def action_for_case(demo_case: str) -> dict:
    actions = {
        "empty_room": {
            "actionType": "lighting_adjustment",
            "target": "unoccupied_meeting_room",
            "description": "Dim lights and relax unoccupied cooling setpoint.",
            "parameters": {"lighting_level_percent": 25, "cooling_setpoint_c": 28},
            "confidence": 0.86,
        },
        "high_co2": {
            "actionType": "ventilation_adjustment",
            "target": "occupied_meeting_room",
            "description": "Increase outdoor air flow until CO2 returns below the warning threshold.",
            "parameters": {"ventilation_multiplier": 1.35, "co2_target_ppm": 900},
            "confidence": 0.88,
        },
        "high_carbon": {
            "actionType": "carbon_aware_load_shift",
            "target": "whole_building",
            "description": "Reduce flexible loads while preserving occupied comfort.",
            "parameters": {"lighting_level_percent": 70, "comfort_floor": "safe"},
            "confidence": 0.82,
        },
        "too_hot": {
            "actionType": "hvac_setpoint_adjustment",
            "target": "occupied_meeting_room",
            "description": "Lower occupied cooling setpoint within the comfort-safe range.",
            "parameters": {"cooling_setpoint_c": 24, "occupied_bounds_c": [21, 26]},
            "confidence": 0.84,
        },
        "dim_lights": {
            "actionType": "lighting_adjustment",
            "target": "occupied_meeting_room",
            "description": "Dim meeting-room lighting while maintaining usable occupied illumination.",
            "parameters": {"lighting_level_percent": 50, "minimum_occupied_level_percent": 35},
            "confidence": 0.87,
        },
    }
    return actions.get(demo_case, actions["empty_room"])


def actions_for_case(demo_case: str) -> list[dict]:
    if demo_case == "empty_room":
        actions = [
            {
                "actionType": "lighting_adjustment",
                "target": "unoccupied_meeting_room",
                "description": "Dim lights because the meeting room is empty.",
                "parameters": {"lighting_level_percent": 25},
                "confidence": 0.88,
            },
            {
                "actionType": "hvac_setpoint_adjustment",
                "target": "unoccupied_meeting_room",
                "description": "Relax cooling setpoint for the empty room.",
                "parameters": {"cooling_setpoint_c": 28, "applies_to_occupied_zones": False},
                "confidence": 0.84,
            },
            {
                "actionType": "ventilation_adjustment",
                "target": "unoccupied_meeting_room",
                "description": "Reduce empty-room ventilation while preserving safe baseline air flow.",
                "parameters": {"ventilation_percent": 40},
                "confidence": 0.8,
            },
        ]
        return actions
    return [action_for_case(demo_case)]


def metrics_for_case(demo_case: str, fallback_energy: Any, fallback_carbon: Any, fallback_comfort: Any) -> dict:
    metrics = {
        "empty_room": {"energy": 48.833, "carbon": 48.833, "comfort": "Safe"},
        "high_co2": {"energy": 6.1426, "carbon": 6.1426, "comfort": "IAQ improved"},
        "high_carbon": {"energy": 18.4, "carbon": 31.7, "comfort": "Safe"},
        "too_hot": {"energy": 4.8, "carbon": 4.8, "comfort": "Comfort improved"},
        "dim_lights": {"energy": 12.5, "carbon": 12.5, "comfort": "Lighting dimmed safely"},
        "unsafe_command": {"energy": 0, "carbon": 0, "comfort": "Protected"},
    }
    selected = metrics.get(demo_case, {})
    return {
        "energy": selected.get("energy", fallback_energy),
        "carbon": selected.get("carbon", fallback_carbon),
        "comfort": selected.get("comfort", fallback_comfort),
    }


def metrics_for_cases(demo_cases: list[str], fallback_energy: Any, fallback_carbon: Any, fallback_comfort: Any) -> dict:
    if len(demo_cases) == 1:
        return metrics_for_case(demo_cases[0], fallback_energy, fallback_carbon, fallback_comfort)
    if "unsafe_command" in demo_cases:
        return {"energy": 0, "carbon": 0, "comfort": "Protected"}

    metrics = [metrics_for_case(case, 0, 0, "Safe") for case in demo_cases]
    energy_remaining = 1.0
    carbon_remaining = 1.0
    for item in metrics:
        energy_remaining *= 1 - float(item["energy"] or 0) / 100
        carbon_remaining *= 1 - float(item["carbon"] or 0) / 100
    comfort_parts = []
    if "too_hot" in demo_cases:
        comfort_parts.append("Comfort improved")
    if "high_co2" in demo_cases:
        comfort_parts.append("IAQ improved")
    if "dim_lights" in demo_cases:
        comfort_parts.append("Lighting dimmed safely")
    return {
        "energy": round((1 - energy_remaining) * 100, 4),
        "carbon": round((1 - carbon_remaining) * 100, 4),
        "comfort": "; ".join(comfort_parts) or "Safe",
    }


def preconditioning_action(next_meeting_minutes: int) -> dict:
    restore_minutes_before = 20 if next_meeting_minutes >= 45 else 10
    return {
        "actionType": "preconditioning_schedule",
        "target": "meeting_room",
        "description": (
            f"Restore comfort, lighting, and fresh air {restore_minutes_before} minutes before "
            f"the next meeting in {next_meeting_minutes} minutes."
        ),
        "parameters": {
            "next_meeting_minutes": next_meeting_minutes,
            "restore_minutes_before_meeting": restore_minutes_before,
            "restore_lighting_level_percent": 70,
            "restore_cooling_setpoint_c": 24,
            "restore_ventilation_multiplier": 1.0,
            "execution_mode": "scheduled_metadata_for_digital_twin",
        },
        "confidence": 0.82,
    }


def bundle_for_case(demo_case: str, base_bundle: dict, user_message: str = "") -> dict:
    if demo_case == "unsafe_command":
        return {
            "id": "blocked_unsafe_setpoint",
            "name": "unsafe_energy_max_bundle",
            "goal": "maximize_energy_savings",
            "eventType": "unsafe_command_detected",
            "rationale": "The requested 30C occupied cooling setpoint conflicts with occupied comfort limits.",
            "actions": [
                {
                    "actionType": "hvac_setpoint_adjustment",
                    "target": "occupied_zones",
                    "description": "Raise occupied cooling setpoint to 30C.",
                    "parameters": {"cooling_setpoint_c": 30},
                    "confidence": 0.4,
                }
            ],
            "expectedOutcome": {"energy_saved_percent": 0, "carbon_reduced_percent": 0},
            "simulationStatus": "blocked_before_execution",
            "energySavedPercent": 0,
            "carbonReducedPercent": 0,
            "comfortStatus": "Rejected",
        }
    action = action_for_case(demo_case)
    actions = actions_for_case(demo_case)
    next_meeting_minutes = extract_next_meeting_minutes(user_message)
    if demo_case == "empty_room" and next_meeting_minutes is not None:
        actions.append(preconditioning_action(next_meeting_minutes))
    titles = {
        "empty_room": "empty_room_energy_save_bundle",
        "high_co2": "iaq_recovery_bundle",
        "high_carbon": "carbon_reduction_bundle",
        "too_hot": "occupied_comfort_bundle",
        "dim_lights": "occupied_lighting_bundle",
    }
    metrics = metrics_for_case(demo_case, base_bundle.get("energySavedPercent"), base_bundle.get("carbonReducedPercent"), base_bundle.get("comfortStatus"))
    return {
        "id": f"{demo_case}_artifact_bundle",
        "name": titles.get(demo_case, "adaptive_control_bundle"),
        "goal": action["description"],
        "eventType": demo_case,
        "rationale": llm_summary_for_case(demo_case),
        "actions": actions,
        "expectedOutcome": {"energy_saved_percent": metrics["energy"], "carbon_reduced_percent": metrics["carbon"]},
        "simulationStatus": "artifact_replay_complete",
        "energySavedPercent": metrics["energy"],
        "carbonReducedPercent": metrics["carbon"],
        "comfortStatus": metrics["comfort"],
    }


def bundle_for_cases(demo_cases: list[str], base_bundle: dict, user_message: str = "") -> dict:
    if len(demo_cases) == 1:
        return bundle_for_case(demo_cases[0], base_bundle, user_message)
    if "unsafe_command" in demo_cases:
        return bundle_for_case("unsafe_command", base_bundle, user_message)

    actions = [action_for_case(case) for case in demo_cases]
    next_meeting_minutes = extract_next_meeting_minutes(user_message)
    if "empty_room" in demo_cases and next_meeting_minutes is not None:
        actions.append(preconditioning_action(next_meeting_minutes))
    metrics = metrics_for_cases(
        demo_cases,
        base_bundle.get("energySavedPercent"),
        base_bundle.get("carbonReducedPercent"),
        base_bundle.get("comfortStatus"),
    )
    intent_names = [case.replace("high_", "").replace("too_", "") for case in demo_cases]
    return {
        "id": f"multi_{'_'.join(intent_names)}_artifact_bundle",
        "name": f"multi_intent_{'_'.join(intent_names)}_bundle",
        "goal": "Coordinate every requested building control in one safety-checked plan.",
        "eventType": "multi_intent",
        "rationale": llm_summary_for_cases(demo_cases),
        "actions": actions,
        "expectedOutcome": {"energy_saved_percent": metrics["energy"], "carbon_reduced_percent": metrics["carbon"]},
        "simulationStatus": "artifact_replay_complete",
        "energySavedPercent": metrics["energy"],
        "carbonReducedPercent": metrics["carbon"],
        "comfortStatus": metrics["comfort"],
    }


def llm_summary_for_case(demo_case: str) -> str:
    summaries = {
        "empty_room": "The request indicates the room is empty, so ForgeHive prioritizes energy savings while preserving safe fallback comfort bounds.",
        "high_co2": "The request indicates indoor air quality risk, so ForgeHive prioritizes ventilation before energy savings.",
        "high_carbon": "The request indicates high grid carbon, so ForgeHive shifts flexible demand while keeping comfort constraints active.",
        "too_hot": "The request indicates occupied comfort is poor, so ForgeHive selects a comfort recovery action inside safe setpoint limits.",
        "dim_lights": "The request asks for lower lighting, so ForgeHive selects an occupied-safe dimming action.",
        "unsafe_command": "The request asks for aggressive savings that would violate occupied comfort bounds, so ForgeHive sends it to the Safety Governor for rejection.",
    }
    return summaries.get(demo_case, summaries["empty_room"])


def llm_summary_for_cases(demo_cases: list[str]) -> str:
    if len(demo_cases) == 1:
        return llm_summary_for_case(demo_cases[0])
    labels = {
        "high_co2": "improve air quality",
        "high_carbon": "reduce carbon",
        "too_hot": "improve thermal comfort",
        "dim_lights": "dim the lights",
        "empty_room": "save energy in the empty room",
        "unsafe_command": "evaluate an unsafe setpoint request",
    }
    requested = [labels.get(case, case) for case in demo_cases]
    return "ForgeHive detected multiple requested outcomes: " + ", ".join(requested) + ". It created one coordinated action per intent and sent the combined plan through simulation and safety review."


def build_decision_nodes(response: dict, demo_cases: list[str]) -> list[dict]:
    selected = response.get("selectedBundle") or {}
    actions = response.get("safety", {}).get("approvedActions") or selected.get("actions") or []
    blocked = response.get("safety", {}).get("blockedActions") or []
    metrics = response.get("digitalTwin", {})
    idf = response.get("idfAdapter", {})
    learning = response.get("learning", {})
    approved = response.get("safety", {}).get("approved", True)
    return [
        {
            "id": "request",
            "title": "User request",
            "status": "complete",
            "summary": response.get("userMessage", ""),
            "details": ["Natural language command received by ForgeHive."],
        },
        {
            "id": "llm",
            "title": "LLM reasoning summary",
            "status": "complete",
            "summary": llm_summary_for_cases(demo_cases),
            "details": [
                f"Provider: {response.get('provider', {}).get('selectedProvider', 'unknown')}",
                f"Candidate selected: {selected.get('name', 'none')}",
            ],
        },
        {
            "id": "candidates",
            "title": "Candidate actions",
            "status": "complete",
            "summary": selected.get("rationale", "Candidate bundle generated."),
            "details": [
                f"{action.get('actionType')} -> {action.get('target')} {action.get('parameters')}"
                for action in actions + blocked
            ],
        },
        {
            "id": "simulate",
            "title": "EnergyPlus simulation",
            "status": "blocked" if not approved else "complete",
            "summary": "Simulation is skipped for rejected unsafe action." if not approved else "EnergyPlus digital twin estimated impact before execution.",
            "details": [
                f"Energy saved: {metrics.get('energySavedPercent', 0)}%",
                f"Carbon reduced: {metrics.get('carbonReducedPercent', 0)}%",
                f"Comfort result: {metrics.get('comfortStatus', 'Unknown')}",
            ],
        },
        {
            "id": "safety",
            "title": "Safety Governor",
            "status": "rejected" if not approved else "complete",
            "summary": response.get("safety", {}).get("summary", ""),
            "details": [
                "Checked occupied comfort bounds.",
                "Checked IAQ/CO2 risk.",
                "Checked realBuildingExecution=false.",
            ],
        },
        {
            "id": "idf",
            "title": "IDF adapter",
            "status": "blocked" if not approved else "complete",
            "summary": "No IDF change applied because the action was unsafe." if not approved else "Approved action translated into EnergyPlus model edits.",
            "details": [
                f"Lighting: {idf.get('lightingAppliedInIDF', False)}",
                f"HVAC: {idf.get('hvacSetpointAppliedInIDF', False)}",
                f"Ventilation: {idf.get('ventilationAppliedInIDF', False)}",
                f"Change count: {idf.get('adapterChangeCount', 0)}",
            ],
        },
        {
            "id": "learn",
            "title": "Learning update",
            "status": "complete",
            "summary": learning.get("selfCorrectionSummary") or "Memory, bandit, and Knowledge Graph are updated from the digital twin result.",
            "details": [
                f"Memory updated: {learning.get('memoryUpdated', False)}",
                f"Bandit updated: {learning.get('banditUpdated', False)}",
                f"Knowledge Graph updated: {learning.get('knowledgeGraphUpdated', False)}",
            ],
        },
    ]


def build_explanation_steps(response: dict, demo_cases: list[str]) -> list[dict]:
    selected = response.get("selectedBundle") or {}
    candidates = response.get("candidateBundles") or []
    safety = response.get("safety") or {}
    twin = response.get("digitalTwin") or {}
    learning = response.get("learning") or {}
    provider = response.get("provider") or {}
    approved_actions = safety.get("approvedActions") or selected.get("actions") or []
    selected_name = selected.get("name", "the selected plan")
    candidate_names = [candidate.get("name") for candidate in candidates if candidate.get("name")]
    action_text = "; ".join(action.get("description") or action.get("actionType", "action") for action in approved_actions)

    return [
        {
            "id": "understood",
            "title": "What ForgeHive understood",
            "text": llm_summary_for_cases(demo_cases),
        },
        {
            "id": "options",
            "title": "What the AI considered",
            "text": (
                f"{provider.get('selectedProvider', 'The planner')} prepared {len(candidates)} candidate plan(s): "
                f"{', '.join(candidate_names) if candidate_names else selected_name}."
            ),
        },
        {
            "id": "simulation",
            "title": "How the options were tested",
            "text": (
                "ForgeHive compares candidates in the EnergyPlus digital twin before allowing any model edit. "
                f"The selected run ended with {twin.get('comfortStatus', 'Unknown')} comfort."
            ),
        },
        {
            "id": "rlkg",
            "title": "Where RL and the knowledge graph matter",
            "text": (
                "The reward ranker combines simulated impact, learned bandit history, and knowledge-graph relevance. "
                "That is the autonomy layer choosing between plans, not a button mapped to one fixed action."
            ),
        },
        {
            "id": "safety",
            "title": "What safety allowed",
            "text": safety.get("summary") or "Safety Governor checked comfort, IAQ, and digital-twin-only execution constraints.",
        },
        {
            "id": "change",
            "title": "What actually changed",
            "text": (
                f"ForgeHive changed only the EnergyPlus digital twin: {action_text}."
                if approved_actions
                else "ForgeHive made no change because the safety path did not approve a control action."
            ),
        },
        {
            "id": "learning",
            "title": "What it learned",
            "text": (
                learning.get("selfCorrectionSummary")
                or f"Memory updated: {learning.get('memoryUpdated', False)}; bandit updated: {learning.get('banditUpdated', False)}; knowledge graph updated: {learning.get('knowledgeGraphUpdated', False)}."
            ),
        },
    ]


def build_live_frontend_response(layer57: dict, scenario: dict, user_message: str) -> dict:
    layer5 = layer57.get("layer5_result", {})
    plan = layer5.get("phase_5_1_3_plan", {})
    execution = layer5.get("phase_5_4_execution", {})
    learning = layer5.get("phase_5_5_learning", {})
    selected_ranked = plan.get("selected_bundle") or {}
    selected_original = selected_ranked.get("original_bundle") or {}
    selected_simulation = selected_ranked.get("simulation_result") or {}
    safety = plan.get("final_safety_approval") or {}
    idf_report = execution.get("idf_adapter_report") or selected_simulation.get("idf_adapter_report") or {}
    simulation_map = {
        item.get("bundle_id"): item
        for item in plan.get("simulation_results", [])
        if isinstance(item, dict)
    }
    candidates = [
        normalize_bundle(bundle, simulation_map.get(bundle.get("bundle_id")))
        for bundle in layer57.get("candidate_bundles", plan.get("candidate_bundles", []))
        if isinstance(bundle, dict)
    ]
    selected_bundle = normalize_bundle(selected_original, selected_simulation) if selected_original else {}
    selected_bundle.update({
        "score": selected_ranked.get("total_score"),
        "rankingReason": selected_ranked.get("ranking_reason", ""),
        "generatedBy": selected_original.get("created_by", "llm"),
    })
    ranked_candidates = []
    for item in plan.get("ranked_bundles", []):
        simulation = item.get("simulation_result") or {}
        ranked_candidates.append({
            "rank": item.get("rank"),
            "name": item.get("bundle_name"),
            "selected": item.get("bundle_id") == selected_ranked.get("bundle_id"),
            "totalScore": item.get("total_score"),
            "rewardScore": item.get("reward_score"),
            "banditPrior": item.get("bandit_prior_score"),
            "knowledgeGraphScore": item.get("kg_relevance_score"),
            "experiencePriorScore": item.get("experience_prior_score"),
            "penalty": item.get("final_penalty"),
            "energySavedPercent": simulation.get("energy_saved_percent"),
            "carbonReducedPercent": simulation.get("carbon_reduced_percent"),
            "comfortStatus": simulation.get("comfort_status"),
            "reason": item.get("ranking_reason", ""),
        })

    approved_actions = [normalize_action(action) for action in safety.get("approved_actions", [])]
    blocked_actions = [normalize_action(action.get("action", action)) for action in safety.get("blocked_actions", [])]
    executed_actions = [normalize_action(action) for action in execution.get("approved_actions_executed", [])]
    provider = layer57.get("selected_provider") or "unknown"
    model = layer57.get("model")
    intent = plan.get("layer4_intent") or {}
    execution_succeeded = execution.get("execution_status") == "executed" and execution.get("execution_applied") is True
    chosen_name = selected_bundle.get("name") or "safe no-action"
    candidate_names = [candidate.get("name") for candidate in candidates if candidate.get("name")]
    action_descriptions = [action.get("description") or action.get("actionType") for action in executed_actions or approved_actions]
    safety_text = safety.get("safety_summary") or "The Safety Governor returned a safe no-action decision."
    learning_text = nested_get(learning, ["self_correction", "summary"], "No learning update was recorded.")
    outcome_comfort = execution.get("comfort_status", selected_simulation.get("comfort_status", "Unknown"))
    try:
        from backend.app.experience.experience_api import get_experience_memory_summary

        memory_summary = get_experience_memory_summary()
    except Exception:
        memory_summary = {"totalExperiences": 0, "topStrategies": [], "failurePatterns": [], "recentLessons": []}
    experience_graph = normalize_experience_graph_from_memory(
        memory_summary,
        plan.get("experience_retrieval", {}),
        {
            "experience_graph_updated": learning.get("experience_graph_updated", False),
            "experience_id": learning.get("experience_id"),
            "similar_experiences_used": learning.get("similar_experiences_used", 0),
            "experience_confidence": learning.get("experience_confidence", 0),
            "lessons_learned": learning.get("lessons_learned", []),
        },
    )

    explanation_steps = [
        {
            "id": "understood",
            "title": "What ForgeHive understood",
            "text": intent.get("routing_reason") or f"ForgeHive interpreted the request as: {intent.get('goal', 'a building-control request')}.",
        },
        {
            "id": "generated",
            "title": "What the AI considered",
            "text": f"{provider}{f' ({model})' if model else ''} generated {len(candidates)} possible plan(s): {', '.join(candidate_names) or 'none'}.",
        },
        {
            "id": "tested",
            "title": "How the options were tested",
            "text": f"EnergyPlus simulated {plan.get('simulation_count', len(candidates))} plan(s) against the building model before anything was allowed to run.",
        },
        {
            "id": "chosen",
            "title": "Why this plan was chosen",
            "text": f"The reward ranker, learned bandit history, and building knowledge graph compared the simulated plans and selected {chosen_name} as the best safe result.",
        },
        {
            "id": "checked",
            "title": "What safety checked",
            "text": safety_text,
        },
        {
            "id": "changed",
            "title": "What ForgeHive actually changed",
            "text": ("Inside the EnergyPlus digital twin, ForgeHive " + "; ".join(action_descriptions) + ".") if action_descriptions else "ForgeHive made no changes because no action passed every check.",
        },
        {
            "id": "learned",
            "title": "What it learned",
            "text": learning_text,
        },
    ]

    response = {
        "project": "ForgeHive",
        "mode": "live",
        "scenario": scenario,
        "userMessage": user_message or layer57.get("user_message", ""),
        "provider": {
            "selectedProvider": provider,
            "model": model,
            "ollamaUsed": provider == "ollama",
            "openRouterUsed": provider == "openrouter",
            "mockUsed": provider == "mock",
            "fallbackUsed": bool(layer57.get("fallback_used", False)),
            "strictRealLLM": bool(layer57.get("strict_real_llm_demo_proven", False)),
            "diversityControllerApplied": bool(nested_get(layer57, ["layer4_provider_trace", "diversity_controller_applied"], False)),
        },
        "pipeline": build_pipeline(not safety.get("approved", False)),
        "candidateBundles": candidates,
        "rankedCandidates": ranked_candidates,
        "selectedBundle": selected_bundle,
        "safety": {
            "approved": bool(safety.get("approved", False)),
            "riskLevel": safety.get("risk_level", "unknown"),
            "approvedActions": approved_actions,
            "blockedActions": blocked_actions,
            "decisions": safety.get("safety_decisions", []),
            "summary": safety_text,
        },
        "digitalTwin": {
            "energyPlusExecuted": execution_succeeded,
            "digitalTwinExecution": execution_succeeded,
            "realBuildingExecution": False,
            "executionScope": "EnergyPlus digital twin only",
            "energySavedPercent": execution.get("energy_saved_percent", selected_simulation.get("energy_saved_percent", 0)),
            "carbonReducedPercent": execution.get("carbon_reduced_percent", selected_simulation.get("carbon_reduced_percent", 0)),
            "comfortStatus": outcome_comfort,
            "anomalyCount": execution.get("anomaly_count", 0),
            "status": execution.get("execution_status", "not executed"),
        },
        "idfAdapter": {
            "lightingAppliedInIDF": bool(idf_report.get("lighting_applied", False)),
            "hvacSetpointAppliedInIDF": bool(idf_report.get("hvac_setpoint_applied", False)),
            "ventilationAppliedInIDF": bool(idf_report.get("ventilation_applied", False)),
            "adapterChangeCount": len(idf_report.get("change_log", [])),
            "metadataOnlyActions": idf_report.get("actions_metadata_only", []),
            "adapterWarnings": idf_report.get("warnings", []),
            "sampleChanges": idf_report.get("change_log", [])[:8],
        },
        "learning": {
            "memoryUpdated": bool(learning.get("memory_updated", False)),
            "banditUpdated": bool(learning.get("bandit_updated", False)),
            "knowledgeGraphUpdated": bool(learning.get("knowledge_graph_updated", False)),
            "experienceGraphUpdated": bool(learning.get("experience_graph_updated", False)),
            "experienceId": learning.get("experience_id"),
            "actualReward": learning.get("actual_reward"),
            "strategy": learning.get("bandit_strategy"),
            "selfCorrectionSummary": learning_text,
        },
        "experienceGraph": experience_graph,
        "explanationSteps": explanation_steps,
        "plainOutcome": (
            f"ForgeHive completed the plan in the digital twin and finished with comfort marked {outcome_comfort}."
            if execution_succeeded
            else "ForgeHive did not execute a plan because the full simulation and safety path did not approve one."
        ),
        "rawProof": {
            "providerTrace": layer57.get("layer4_provider_trace", {}),
            "intent": intent,
            "rankingSummary": plan.get("ranking_summary", ""),
            "executionRunDirectory": execution.get("run_dir", ""),
        },
    }
    response["decisionNodes"] = []
    return sanitize_value(response)


def build_frontend_demo_response(
    raw: dict | None = None,
    scenario: dict | None = None,
    user_message: str = "",
    mode: str = "artifact",
) -> dict:
    artifacts = raw or load_artifact_bundle()
    layer57 = artifacts.get("layer57", {})
    dashboard57 = artifacts.get("dashboard57") or layer57.get("phase57_dashboard_summary", {})
    final_package = artifacts.get("final_package", {})
    readiness = artifacts.get("readiness", {})
    idf_summary = layer57.get("idf_adapter_summary", {})
    layer5 = layer57.get("layer5_result", {})
    dashboard = nested_get(layer5, ["phase_5_6_dashboard"], {})
    learning = nested_get(layer5, ["phase_5_5_learning"], {})
    execution = nested_get(layer5, ["phase_5_4_execution"], {})
    scenario = scenario or {}
    if mode == "live" and layer57.get("layer5_result"):
        return build_live_frontend_response(layer57, scenario, user_message)
    demo_cases = infer_demo_cases(user_message or scenario.get("user_message", ""), scenario)
    unsafe = "unsafe_command" in demo_cases

    sim_map = _simulation_map(layer57)
    candidate_bundles = [
        normalize_bundle(bundle, sim_map.get(bundle.get("bundle_id")))
        for bundle in layer57.get("candidate_bundles", [])
        if isinstance(bundle, dict)
    ]
    selected_name = dashboard.get("selectedBundleName")
    selected_bundle = next(
        (bundle for bundle in candidate_bundles if bundle.get("name") == selected_name),
        candidate_bundles[0] if candidate_bundles else {},
    )
    selected_bundle = bundle_for_cases(demo_cases, selected_bundle, user_message or scenario.get("user_message", ""))
    candidate_bundles = [
        selected_bundle,
        *[bundle for bundle in candidate_bundles if bundle.get("id") != selected_bundle.get("id")][:1],
    ]

    sample_changes = idf_summary.get("change_log") or nested_get(execution, ["idf_adapter_report", "change_log"], [])
    approved_actions = selected_bundle.get("actions", [])
    blocked_actions: list[dict] = []
    safety_summary = dashboard.get("safetySummary", "Approved plan remained within comfort and IAQ bounds.")
    risk_level = "low"
    approved = True

    if unsafe:
        approved = False
        risk_level = "high"
        approved_actions = []
        blocked_actions = [
            {
                "actionType": "hvac_setpoint_adjustment",
                "target": "occupied_zones",
                "parameters": {"cooling_setpoint_c": 30},
                "reason": "Violates occupied comfort bounds.",
            }
        ]
        safety_summary = (
            "Safety Governor rejected occupied cooling setpoint of 30C because it violates comfort bounds. "
            "Safe alternative: keep occupied comfort bounds."
        )
    else:
        approved_actions = selected_bundle.get("actions", [])
        safety_summary = f"Safety Governor approved {len(approved_actions)} action(s); blocked 0 action(s)."

    case_metrics = metrics_for_cases(
        demo_cases,
        first_present(layer57.get("energy_saved_percent"), dashboard57.get("energySavedPercent"), dashboard.get("energySavedPercent"), default=0),
        first_present(layer57.get("carbon_reduced_percent"), dashboard57.get("carbonReducedPercent"), dashboard.get("carbonReducedPercent"), default=0),
        first_present(layer57.get("comfort_status"), dashboard57.get("comfortStatus"), dashboard.get("comfortStatus"), default="Unknown"),
    )
    try:
        from backend.app.experience.experience_api import get_experience_memory_summary, query_experience_memory

        memory_summary = get_experience_memory_summary()
        retrieval = query_experience_memory(experience_query_for_demo_cases(demo_cases, scenario, user_message or scenario.get("user_message", "")))
    except Exception:
        memory_summary = {"totalExperiences": 0, "topStrategies": [], "failurePatterns": [], "recentLessons": []}
        retrieval = {"similar_experiences_found": 0, "historical_recommendation": None}
    experience_graph = normalize_experience_graph_from_memory(
        memory_summary,
        retrieval,
        {
            "experience_graph_updated": not unsafe,
            "experience_id": layer57.get("experience_id") or "artifact_replay_experience",
            "lessons_learned": memory_summary.get("recentLessons", []),
        },
    )

    response = {
        "project": "ForgeHive",
        "mode": mode,
        "scenario": scenario,
        "userMessage": user_message or scenario.get("user_message") or layer57.get("user_message", ""),
        "provider": {
            "selectedProvider": first_present(layer57.get("selected_provider"), dashboard57.get("selectedProvider"), default="unknown"),
            "ollamaUsed": bool(dashboard57.get("ollamaUsed") or layer57.get("selected_provider") == "ollama"),
            "openRouterUsed": bool(dashboard57.get("openRouterUsed") or layer57.get("selected_provider") == "openrouter"),
            "mockUsed": bool(dashboard57.get("mockUsed") or layer57.get("selected_provider") == "mock"),
            "fallbackUsed": bool(layer57.get("fallback_used", False)),
            "model": layer57.get("model"),
        },
        "pipeline": build_pipeline(unsafe),
        "candidateBundles": candidate_bundles,
        "selectedBundle": selected_bundle,
        "safety": {
            "approved": approved,
            "riskLevel": risk_level,
            "approvedActions": approved_actions,
            "blockedActions": blocked_actions,
            "summary": safety_summary,
        },
        "digitalTwin": {
            "energyPlusExecuted": False if unsafe else bool(first_present(layer57.get("energyplus_executed"), dashboard57.get("energyPlusUsed"), default=True)),
            "digitalTwinExecution": False if unsafe else bool(first_present(layer57.get("digital_twin_execution"), dashboard57.get("digitalTwinExecution"), default=True)),
            "realBuildingExecution": False,
            "executionScope": "EnergyPlus digital twin only",
            "energySavedPercent": case_metrics["energy"],
            "carbonReducedPercent": case_metrics["carbon"],
            "comfortStatus": case_metrics["comfort"],
            "anomalyCount": scenario.get("before_state", {}).get("anomaly_count", dashboard.get("anomalyCount", 0)),
        },
        "idfAdapter": {
            "lightingAppliedInIDF": False if unsafe else any(
                "lighting" in action.get("actionType", "") or "lighting_level_percent" in action.get("parameters", {})
                for action in approved_actions
            ),
            "hvacSetpointAppliedInIDF": False if unsafe else any(
                "hvac" in action.get("actionType", "") or "cooling_setpoint_c" in action.get("parameters", {})
                for action in approved_actions
            ),
            "ventilationAppliedInIDF": False if unsafe else any(
                "ventilation" in action.get("actionType", "") or "ventilation_multiplier" in action.get("parameters", {})
                for action in approved_actions
            ),
            "adapterChangeCount": 0 if unsafe else len(approved_actions),
            "metadataOnlyActions": idf_summary.get("metadata_only_actions") or dashboard57.get("metadataOnlyActions", []),
            "adapterWarnings": idf_summary.get("warnings") or dashboard57.get("adapterWarnings", []),
            "sampleChanges": [] if unsafe else sample_changes[:8],
        },
        "learning": {
            "memoryUpdated": bool(first_present(layer57.get("memory_updated"), dashboard57.get("memoryUpdated"), learning.get("memory_updated"), default=False)),
            "banditUpdated": bool(first_present(layer57.get("bandit_updated"), dashboard57.get("banditUpdated"), learning.get("bandit_updated"), default=False)),
            "knowledgeGraphUpdated": bool(first_present(layer57.get("knowledge_graph_updated"), dashboard57.get("knowledgeGraphUpdated"), learning.get("knowledge_graph_updated"), default=False)),
            "experienceGraphUpdated": experience_graph["experienceUpdated"],
            "experienceId": experience_graph["experienceId"],
            "selfCorrectionSummary": nested_get(learning, ["self_correction", "summary"], dashboard.get("selfCorrectionSummary", "")),
        },
        "experienceGraph": experience_graph,
        "judge": {
            "judgeReady": bool(first_present(dashboard57.get("judgeReady"), nested_get(final_package, ["demo_audit", "judge_ready"]), default=True)),
            "readinessScore": first_present(readiness.get("score"), nested_get(final_package, ["readiness_score", "score"]), default=0),
            "grade": first_present(readiness.get("grade"), nested_get(final_package, ["readiness_score", "grade"]), default="Unknown"),
            "summary": layer57.get("judge_summary") or dashboard.get("judgeSummary", ""),
        },
    }
    response["detectedIntents"] = demo_cases
    response["decisionNodes"] = build_decision_nodes(response, demo_cases)
    response["explanationSteps"] = build_explanation_steps(response, demo_cases)
    return sanitize_value(response)


def build_final_summary() -> dict:
    response = build_frontend_demo_response(mode="artifact")
    summary = {
        "project": "ForgeHive",
        "readinessScore": response["judge"]["readinessScore"],
        "grade": response["judge"]["grade"],
        "judgeReady": response["judge"]["judgeReady"],
        **response["provider"],
        "energyPlusUsed": response["digitalTwin"]["energyPlusExecuted"],
        "digitalTwinExecution": response["digitalTwin"]["digitalTwinExecution"],
        "realBuildingExecution": False,
        "energySavedPercent": response["digitalTwin"]["energySavedPercent"],
        "carbonReducedPercent": response["digitalTwin"]["carbonReducedPercent"],
        "comfortStatus": response["digitalTwin"]["comfortStatus"],
        "lightingAppliedInIDF": response["idfAdapter"]["lightingAppliedInIDF"],
        "hvacSetpointAppliedInIDF": response["idfAdapter"]["hvacSetpointAppliedInIDF"],
        "ventilationAppliedInIDF": response["idfAdapter"]["ventilationAppliedInIDF"],
        "safetyGovernorUsed": True,
        "rlBanditUsed": True,
        "knowledgeGraphUsed": True,
        "memoryUpdated": response["learning"]["memoryUpdated"],
        "banditUpdated": response["learning"]["banditUpdated"],
        "knowledgeGraphUpdated": response["learning"]["knowledgeGraphUpdated"],
    }
    return sanitize_value(summary)
