from backend.app.cognitive.request_semantics import analyze_user_request


INTENT_MAPPINGS = {
    "empty_room_energy_saving": {
        "goal": "reduce_energy_keep_comfort_safe",
        "event_type": "empty_room_detected",
        "action_oriented": True,
    },
    "carbon_reduction": {
        "goal": "reduce_carbon",
        "event_type": "high_carbon_window",
        "action_oriented": True,
    },
    "comfort_protection": {
        "goal": "maintain_comfort",
        "event_type": "comfort_request",
        "action_oriented": True,
    },
    "iaq_improvement": {
        "goal": "improve_iaq",
        "event_type": "iaq_risk_detected",
        "action_oriented": True,
    },
    "lighting_improvement": {
        "goal": "improve_occupied_lighting",
        "event_type": "lighting_issue_detected",
        "action_oriented": True,
    },
    "multi_objective_control": {
        "goal": "resolve_occupied_multi_issue",
        "event_type": "occupied_multi_issue_detected",
        "action_oriented": True,
    },
    "anomaly_response": {
        "goal": "fix_anomalies",
        "event_type": "anomaly_detected",
        "action_oriented": True,
    },
    "explain_decision": {
        "goal": "explain_current_decision",
        "event_type": "explanation_requested",
        "action_oriented": False,
    },
    "safety_review": {
        "goal": "review_safety_guardrails",
        "event_type": "safety_review_requested",
        "action_oriented": False,
    },
    "general_building_status": {
        "goal": "summarize_building_status",
        "event_type": "status_requested",
        "action_oriented": False,
    },
}


ROUTING_RULES = [
    ("empty_room_energy_saving", ["empty", "vacant", "meeting ended", "room is free", "nobody inside"]),
    ("carbon_reduction", ["carbon", "emission", "grid intensity", "co2 footprint"]),
    ("comfort_protection", ["too hot", "too cold", "temperature", "comfort", "uncomfortable"]),
    ("iaq_improvement", ["co2", "stuffy", "suffocat", "air quality", "iaq", "ventilation", "fresh air"]),
    ("lighting_improvement", ["poor light", "poor lighting", "lighting is poor", "too dark", "can't see", "cannot see", "low light", "too bright", "glare"]),
    ("anomaly_response", ["anomaly", "fault", "abnormal", "equipment", "failure", "sensor issue"]),
    ("explain_decision", ["why", "explain", "reason", "chosen", "decision"]),
    ("safety_review", ["safe", "unsafe", "guardrail", "risk", "safety"]),
    ("general_building_status", ["status", "score", "health", "summary", "how is building"]),
]


def classify_operator_intent(user_message: str) -> dict:
    text = (user_message or "").lower()
    analysis = analyze_user_request(user_message)
    issue_intents = []
    issue_to_intent = {
        "high_temperature": "comfort_protection",
        "low_temperature": "comfort_protection",
        "poor_air_quality": "iaq_improvement",
        "insufficient_lighting": "lighting_improvement",
        "excessive_lighting": "lighting_improvement",
    }
    for issue in analysis["issues"]:
        intent_name = issue_to_intent.get(issue)
        if intent_name and intent_name not in issue_intents:
            issue_intents.append(intent_name)

    if len(issue_intents) > 1:
        mapping = INTENT_MAPPINGS["multi_objective_control"]
        goal_parts = []
        if "comfort_protection" in issue_intents:
            goal_parts.append("comfort")
        if "iaq_improvement" in issue_intents:
            goal_parts.append("iaq")
        if "lighting_improvement" in issue_intents:
            goal_parts.append("lighting")
        return {
            "intent": "multi_objective_control",
            "goal": "resolve_occupied_" + "_".join(goal_parts),
            "event_type": mapping["event_type"],
            "confidence": 0.95,
            "routing_reason": "Detected multiple occupied-space needs: " + ", ".join(analysis["issues"]) + ".",
            "action_oriented": True,
            "matched_intents": issue_intents,
            "request_analysis": analysis,
        }

    for intent, keywords in ROUTING_RULES:
        matched_keyword = next((keyword for keyword in keywords if keyword in text), None)
        if matched_keyword:
            mapping = INTENT_MAPPINGS[intent]
            return {
                "intent": intent,
                "goal": mapping["goal"],
                "event_type": mapping["event_type"],
                "confidence": 0.9,
                "routing_reason": f"Matched keyword '{matched_keyword}'.",
                "action_oriented": mapping["action_oriented"],
                "matched_intents": [intent],
                "request_analysis": analysis,
            }

    mapping = INTENT_MAPPINGS["general_building_status"]
    return {
        "intent": "general_building_status",
        "goal": mapping["goal"],
        "event_type": mapping["event_type"],
        "confidence": 0.55,
        "routing_reason": "No action-specific keyword matched; defaulted to building status.",
        "action_oriented": mapping["action_oriented"],
        "matched_intents": [],
        "request_analysis": analysis,
    }
