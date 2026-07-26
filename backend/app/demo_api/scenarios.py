SCENARIOS = [
    {
        "id": "empty_room",
        "title": "Meeting room became empty",
        "user_message": "The meeting room is empty now. Save energy but keep comfort safe.",
        "before_state": {
            "occupancy": 0,
            "temperature_c": 24,
            "co2_ppm": 650,
            "comfort_status": "Safe",
            "anomaly_count": 0,
        },
    },
    {
        "id": "high_co2",
        "title": "CO2 is too high",
        "user_message": "CO2 is too high in the meeting room. Fix air quality while keeping energy reasonable.",
        "before_state": {
            "occupancy": 12,
            "temperature_c": 24,
            "co2_ppm": 1200,
            "comfort_status": "Warning",
            "anomaly_count": 1,
        },
    },
    {
        "id": "high_carbon",
        "title": "Grid carbon is high",
        "user_message": "Carbon intensity is high today. Reduce carbon impact without hurting comfort.",
        "before_state": {
            "occupancy": 20,
            "temperature_c": 24,
            "carbon_intensity": "High",
            "comfort_status": "Safe",
            "anomaly_count": 0,
        },
    },
    {
        "id": "too_hot",
        "title": "User says room is too hot",
        "user_message": "The room is too hot. Improve comfort safely.",
        "before_state": {
            "occupancy": 8,
            "temperature_c": 29,
            "co2_ppm": 700,
            "comfort_status": "Warning",
            "anomaly_count": 0,
        },
    },
    {
        "id": "unsafe_command",
        "title": "Unsafe command attempted",
        "user_message": "Set occupied cooling setpoint to 30C to save maximum energy.",
        "before_state": {
            "occupancy": 15,
            "temperature_c": 24,
            "comfort_status": "Safe",
            "anomaly_count": 0,
        },
    },
]


def get_scenarios() -> list[dict]:
    return [dict(scenario) for scenario in SCENARIOS]


def get_scenario(scenario_id: str) -> dict | None:
    for scenario in SCENARIOS:
        if scenario["id"] == scenario_id:
            return dict(scenario)
    return None

