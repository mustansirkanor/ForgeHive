from backend.app.intelligence.schemas import BuildingState, ComfortState, ZoneState


OCCUPIED_MIN_TEMP_C = 21.0
OCCUPIED_MAX_TEMP_C = 26.0
UNOCCUPIED_MIN_TEMP_C = 18.0
UNOCCUPIED_MAX_TEMP_C = 30.0
CO2_COMFORT_THRESHOLD_PPM = 1000.0


def clamp(value, min_value, max_value) -> float:
    return max(min_value, min(float(value), max_value))


def calculate_pmv_proxy(temperature_c: float, humidity_percent: float) -> float:
    neutral_temp = 23.5
    temp_component = (temperature_c - neutral_temp) / 2.5
    humidity_component = (humidity_percent - 50) / 50
    pmv_proxy = temp_component + 0.2 * humidity_component
    return clamp(pmv_proxy, -3.0, 3.0)


def evaluate_zone_comfort(zone: ZoneState) -> dict:
    occupied = zone.occupancy_count > 0
    min_temp = OCCUPIED_MIN_TEMP_C if occupied else UNOCCUPIED_MIN_TEMP_C
    max_temp = OCCUPIED_MAX_TEMP_C if occupied else UNOCCUPIED_MAX_TEMP_C

    violations = []
    comfort_penalty = 0.0
    comfort_violation_minutes = 0

    if not min_temp <= zone.temperature_c <= max_temp:
        range_label = "occupied" if occupied else "unoccupied"
        violations.append(
            f"{zone.zone_id} temperature {zone.temperature_c:.1f}C is outside "
            f"the {range_label} comfort range {min_temp:.1f}C-{max_temp:.1f}C."
        )
        if occupied:
            comfort_penalty += 15.0
            comfort_violation_minutes += 15
        else:
            comfort_penalty += 5.0
            comfort_violation_minutes += 5

    if occupied and zone.co2_ppm > CO2_COMFORT_THRESHOLD_PPM:
        violations.append(
            f"{zone.zone_id} CO2 {zone.co2_ppm:.0f} ppm exceeds the occupied threshold "
            f"of {CO2_COMFORT_THRESHOLD_PPM:.0f} ppm."
        )
        comfort_penalty += 10.0
        comfort_violation_minutes += 10

    if not violations:
        status = "comfortable"
    elif occupied:
        status = "violation"
    else:
        status = "warning"

    return {
        "zone_id": zone.zone_id,
        "status": status,
        "pmv_proxy": calculate_pmv_proxy(zone.temperature_c, zone.humidity_percent),
        "violations": violations,
        "comfort_penalty": comfort_penalty,
        "comfort_violation_minutes": comfort_violation_minutes,
    }


def evaluate_building_comfort(state: BuildingState) -> ComfortState:
    zone_results = [evaluate_zone_comfort(zone) for zone in state.zones]

    if zone_results:
        average_pmv_proxy = sum(result["pmv_proxy"] for result in zone_results) / len(zone_results)
    else:
        average_pmv_proxy = 0.0

    comfort_violation_minutes = sum(result["comfort_violation_minutes"] for result in zone_results)
    total_penalty = sum(result["comfort_penalty"] for result in zone_results)
    violations = [
        violation
        for result in zone_results
        for violation in result["violations"]
    ]
    has_occupied_violations = any(result["status"] == "violation" for result in zone_results)

    comfort_score = clamp(100.0 - total_penalty, 0.0, 100.0)

    if comfort_score >= 90 and not has_occupied_violations:
        status = "Safe"
    elif comfort_score >= 70:
        status = "Warning"
    else:
        status = "Unsafe"

    return ComfortState(
        comfort_score=comfort_score,
        comfort_violation_minutes=comfort_violation_minutes,
        pmv_proxy=clamp(average_pmv_proxy, -3.0, 3.0),
        status=status,
        violations=violations,
        source="phase_2_3_comfort_engine",
    )


def apply_comfort_engine(state: BuildingState) -> BuildingState:
    zone_results = {
        result["zone_id"]: result
        for result in (evaluate_zone_comfort(zone) for zone in state.zones)
    }

    for zone in state.zones:
        result = zone_results.get(zone.zone_id)
        if result:
            zone.comfort_status = result["status"]

    state.comfort = evaluate_building_comfort(state)
    return state


def comfort_summary_dict(state: BuildingState) -> dict:
    return {
        "comfort_score": state.comfort.comfort_score,
        "comfort_violation_minutes": state.comfort.comfort_violation_minutes,
        "pmv_proxy": state.comfort.pmv_proxy,
        "status": state.comfort.status,
        "violations": state.comfort.violations,
    }
