from datetime import datetime, timezone
from typing import Any


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    number = safe_float(value)
    return int(number) if number is not None else None


def get_nested(data: dict, paths: list[list[str]], default=None):
    for path in paths:
        current = data
        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if current is not None:
            return current
    return default


def text_similarity(left: Any, right: Any) -> float:
    if left is None or right is None:
        return 0.0
    return 1.0 if str(left).lower() == str(right).lower() else 0.0


def numeric_similarity(left: Any, right: Any, max_delta: float) -> float:
    left_number = safe_float(left)
    right_number = safe_float(right)
    if left_number is None or right_number is None:
        return 0.0
    return max(0.0, 1.0 - min(abs(left_number - right_number), max_delta) / max_delta)


def range_similarity(left: Any, right: Any, ranges: list[tuple[float, float]]) -> float:
    left_number = safe_float(left)
    right_number = safe_float(right)
    if left_number is None or right_number is None:
        return 0.0
    for low, high in ranges:
        if low <= left_number <= high and low <= right_number <= high:
            return 1.0
    return numeric_similarity(left_number, right_number, max(abs(high - low) for low, high in ranges))


def calculate_situation_similarity(current: dict, previous: dict) -> float:
    current = current or {}
    previous = previous or {}
    weights = {
        "event_type": 0.30,
        "goal": 0.20,
        "occupancy": 0.15,
        "comfort_status": 0.10,
        "carbon_state": 0.10,
        "anomaly_count": 0.05,
        "co2_ppm": 0.05,
        "next_meeting_minutes": 0.05,
    }
    score = 0.0
    score += weights["event_type"] * text_similarity(current.get("event_type"), previous.get("event_type"))
    score += weights["goal"] * text_similarity(current.get("goal"), previous.get("goal"))
    score += weights["occupancy"] * numeric_similarity(current.get("occupancy"), previous.get("occupancy"), 25)
    score += weights["comfort_status"] * text_similarity(current.get("comfort_status"), previous.get("comfort_status"))
    score += weights["carbon_state"] * text_similarity(current.get("carbon_state"), previous.get("carbon_state"))
    score += weights["anomaly_count"] * numeric_similarity(current.get("anomaly_count"), previous.get("anomaly_count"), 5)
    score += weights["co2_ppm"] * range_similarity(current.get("co2_ppm"), previous.get("co2_ppm"), [(0, 800), (801, 1000), (1001, 1400), (1401, 5000)])
    score += weights["next_meeting_minutes"] * range_similarity(current.get("next_meeting_minutes"), previous.get("next_meeting_minutes"), [(0, 30), (31, 60), (61, 120), (121, 9999)])
    return round(max(0.0, min(1.0, score)), 4)


def normalize_occupancy(value: Any) -> int | None:
    if isinstance(value, dict):
        return safe_int(value.get("total_occupancy") or value.get("count") or value.get("occupancy"))
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"unoccupied", "empty", "vacant"}:
            return 0
        if lowered == "occupied":
            return 1
    return safe_int(value)


def extract_situation_signature_from_context(context: dict) -> dict:
    context = context or {}
    building_state = get_nested(context, [["building_state"], ["buildingState"], ["state"], ["before_state"], ["building_context", "building_state"]], {}) or {}
    analysis = get_nested(context, [["request_analysis"], ["extra_context", "request_analysis"], ["intent", "request_analysis"], ["layer4_intent", "request_analysis"]], {}) or {}
    comfort = get_nested(context, [["comfort"], ["building_context", "comfort"]], {}) or {}
    anomalies = get_nested(context, [["anomalies"], ["building_context", "anomalies"]], {}) or {}

    occupancy = normalize_occupancy(
        context.get("occupancy")
        if "occupancy" in context
        else building_state.get("occupancy")
        if "occupancy" in building_state
        else analysis.get("occupancy")
        if analysis.get("occupancy") is not None
        else get_nested(context, [["dashboard", "occupancy"], ["scenario", "before_state", "occupancy"]])
    )
    carbon_state = (
        context.get("carbon_state")
        or building_state.get("carbon_state")
        or building_state.get("carbon_intensity")
        or context.get("carbon_intensity")
        or get_nested(context, [["scenario", "before_state", "carbon_state"], ["scenario", "before_state", "carbon_intensity"]])
    )
    return {
        "event_type": context.get("event_type") or get_nested(context, [["normalized", "event_type"], ["intent", "event_type"], ["layer4_intent", "event_type"]], "operator_request"),
        "goal": context.get("goal") or get_nested(context, [["normalized", "goal"], ["intent", "goal"], ["layer4_intent", "goal"]], "balanced_optimization"),
        "occupancy": occupancy,
        "temperature_c": safe_float(context.get("temperature_c") or building_state.get("temperature_c") or get_nested(context, [["scenario", "before_state", "temperature_c"]])),
        "co2_ppm": safe_float(context.get("co2_ppm") or building_state.get("co2_ppm") or get_nested(context, [["scenario", "before_state", "co2_ppm"]])),
        "carbon_state": str(carbon_state).lower() if carbon_state is not None else None,
        "next_meeting_minutes": safe_int(context.get("next_meeting_minutes") or analysis.get("next_meeting_minutes") or get_nested(context, [["extra_context", "next_meeting_minutes"]])),
        "comfort_status": context.get("comfort_status") or building_state.get("comfort_status") or comfort.get("status") or get_nested(context, [["building_summary", "comfort_status"], ["scenario", "before_state", "comfort_status"]], None),
        "anomaly_count": safe_int(context.get("anomaly_count") if "anomaly_count" in context else building_state.get("anomaly_count") if "anomaly_count" in building_state else anomalies.get("anomaly_count") if anomalies else get_nested(context, [["building_summary", "anomaly_count"], ["scenario", "before_state", "anomaly_count"]], 0)),
        "timestamp": context.get("timestamp") or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }

