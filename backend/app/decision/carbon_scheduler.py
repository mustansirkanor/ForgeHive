import uuid

from backend.app.decision.action_schema import ControlAction
from backend.app.intelligence.intelligence_api import get_building_intelligence_package


def classify_carbon_intensity(value: float) -> str:
    if value <= 0.35:
        return "low"
    if value <= 0.50:
        return "medium"
    return "high"


def get_simulated_carbon_forecast() -> list[dict]:
    hourly_values = [
        0.32,
        0.31,
        0.30,
        0.30,
        0.31,
        0.33,
        0.35,
        0.42,
        0.45,
        0.48,
        0.50,
        0.54,
        0.58,
        0.60,
        0.59,
        0.56,
        0.53,
        0.52,
        0.51,
        0.49,
        0.47,
        0.44,
        0.34,
        0.32,
    ]

    return [
        {
            "hour": hour,
            "carbon_intensity_kg_per_kwh": value,
            "label": classify_carbon_intensity(value),
        }
        for hour, value in enumerate(hourly_values)
    ]


def find_windows(forecast: list[dict], label: str) -> list[dict]:
    windows = []
    current = []

    for record in forecast:
        if record["label"] == label:
            current.append(record)
        elif current:
            windows.append(build_window(current))
            current = []

    if current:
        windows.append(build_window(current))

    return windows


def build_window(records: list[dict]) -> dict:
    avg_intensity = sum(record["carbon_intensity_kg_per_kwh"] for record in records) / len(records)
    return {
        "start_hour": records[0]["hour"],
        "end_hour": records[-1]["hour"],
        "avg_carbon_intensity": round(avg_intensity, 3),
    }


def find_low_carbon_windows(forecast: list[dict]) -> list[dict]:
    return find_windows(forecast, "low")


def find_high_carbon_windows(forecast: list[dict]) -> list[dict]:
    return find_windows(forecast, "high")


def build_carbon_aware_plan(intelligence: dict | None = None) -> dict:
    current_intelligence = intelligence if intelligence is not None else get_building_intelligence_package()
    forecast = get_simulated_carbon_forecast()
    low_windows = find_low_carbon_windows(forecast)
    high_windows = find_high_carbon_windows(forecast)
    recommended_schedule = []

    if low_windows and high_windows:
        first_low = low_windows[0]
        first_high = high_windows[0]
        recommended_schedule.append(
            {
                "action": "precondition",
                "start_hour": first_low["start_hour"],
                "end_hour": first_low["end_hour"],
                "reason": "Use lower-carbon electricity before carbon peak.",
            }
        )
        recommended_schedule.append(
            {
                "action": "reduce_flexible_load",
                "start_hour": first_high["start_hour"],
                "end_hour": first_high["end_hour"],
                "reason": "Avoid high-carbon operation while preserving comfort.",
            }
        )

    return {
        "strategy_name": "carbon_aware_mode",
        "forecast": forecast,
        "low_carbon_windows": low_windows,
        "high_carbon_windows": high_windows,
        "recommended_schedule": recommended_schedule,
        "expected_carbon_reduced_percent": 6.0,
        "expected_energy_saved_percent": 3.0,
        "comfort_guard_enabled": True,
        "context": {
            "comfort_status": current_intelligence.get("comfort", {}).get("status", "Safe"),
            "overall_score": current_intelligence.get("score", {}).get("overall", 0),
        },
    }


def create_carbon_schedule_action(plan: dict) -> ControlAction:
    return ControlAction(
        action_id=str(uuid.uuid4()),
        strategy_name="carbon_aware_mode",
        action_type="carbon_schedule_shift",
        target="whole_building",
        description="Shift flexible HVAC and lighting operations toward lower-carbon windows while keeping comfort safe.",
        parameters={
            "recommended_schedule": plan["recommended_schedule"],
            "comfort_guard_enabled": True,
            "preconditioning_enabled": True,
        },
        expected_energy_saved_percent=plan["expected_energy_saved_percent"],
        expected_carbon_reduced_percent=plan["expected_carbon_reduced_percent"],
        expected_comfort_impact="neutral",
        source_agent="carbon_scheduler",
        priority="medium",
    )
