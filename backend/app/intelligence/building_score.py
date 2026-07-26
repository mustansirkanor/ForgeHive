from backend.app.intelligence.comfort_engine import apply_comfort_engine
from backend.app.intelligence.state_extractor import extract_building_state_from_latest_run


LAYER_1_BASELINE_ELECTRICITY_KWH = 43510.13
LAYER_1_BASELINE_CARBON_KG = 19579.56


def clamp(value, min_value, max_value) -> float:
    return max(min_value, min(float(value), max_value))


def calculate_energy_efficiency_score(electricity_kwh: float, baseline_kwh: float | None = None) -> float:
    baseline = baseline_kwh if baseline_kwh is not None else LAYER_1_BASELINE_ELECTRICITY_KWH

    if baseline <= 0:
        return 75.0

    energy_saved_percent = ((baseline - electricity_kwh) / baseline) * 100
    score = 75 + (energy_saved_percent * 2)
    return clamp(score, 0.0, 100.0)


def calculate_carbon_score(carbon_kg: float, baseline_carbon_kg: float | None = None) -> float:
    baseline = baseline_carbon_kg if baseline_carbon_kg is not None else LAYER_1_BASELINE_CARBON_KG

    if baseline <= 0:
        return 75.0

    carbon_saved_percent = ((baseline - carbon_kg) / baseline) * 100
    score = 75 + (carbon_saved_percent * 2)
    return clamp(score, 0.0, 100.0)


def calculate_equipment_health_score(state) -> float:
    score = 90.0

    if state.energy.electricity_kwh > 0:
        hvac_ratio = state.energy.hvac_kwh / state.energy.electricity_kwh
        if hvac_ratio > 0.25:
            score -= 10.0

    return clamp(score, 0.0, 100.0)


def calculate_anomaly_risk_score(state) -> float:
    score = 96.0

    if any(zone.co2_ppm > 1000 for zone in state.zones):
        score -= 10.0

    if any(zone.lighting_level_percent > 90 and zone.occupancy_count == 0 for zone in state.zones):
        score -= 10.0

    if state.comfort.status == "Unsafe":
        score -= 20.0

    return clamp(score, 0.0, 100.0)


def grade_from_overall(overall: float) -> str:
    if overall >= 90:
        return "Excellent"
    if overall >= 80:
        return "Good"
    if overall >= 70:
        return "Needs Attention"
    return "Critical"


def summary_from_grade(grade: str) -> str:
    summaries = {
        "Excellent": "ForgeHive is operating efficiently while maintaining comfort and carbon performance.",
        "Good": "ForgeHive performance is stable with minor optimization opportunities.",
        "Needs Attention": "ForgeHive detected areas that need operational improvement.",
        "Critical": "ForgeHive detected serious building performance risks.",
    }
    return summaries[grade]


def calculate_building_intelligence_score(state) -> dict:
    energy_efficiency = calculate_energy_efficiency_score(state.energy.electricity_kwh)
    comfort = clamp(state.comfort.comfort_score, 0.0, 100.0)
    carbon_optimization = calculate_carbon_score(state.carbon.carbon_kg)
    equipment_health = calculate_equipment_health_score(state)
    anomaly_risk = calculate_anomaly_risk_score(state)

    overall = round(
        (energy_efficiency * 0.25)
        + (comfort * 0.25)
        + (carbon_optimization * 0.20)
        + (equipment_health * 0.15)
        + (anomaly_risk * 0.15),
        2,
    )
    grade = grade_from_overall(overall)

    return {
        "energy_efficiency": round(energy_efficiency, 2),
        "comfort": round(comfort, 2),
        "carbon_optimization": round(carbon_optimization, 2),
        "equipment_health": round(equipment_health, 2),
        "anomaly_risk": round(anomaly_risk, 2),
        "overall": overall,
        "grade": grade,
        "summary": summary_from_grade(grade),
    }


def get_latest_building_score() -> dict:
    state = extract_building_state_from_latest_run()
    state = apply_comfort_engine(state)
    return calculate_building_intelligence_score(state)
