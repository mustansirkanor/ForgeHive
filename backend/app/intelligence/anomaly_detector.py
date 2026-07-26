from backend.app.intelligence.comfort_engine import apply_comfort_engine
from backend.app.intelligence.state_extractor import extract_building_state_from_latest_run


BASELINE_ELECTRICITY_KWH = 43510.13
SEVERITY_PRIORITY = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def create_anomaly(
    anomaly_type: str,
    severity: str,
    message: str,
    recommended_action: str,
    evidence: dict | None = None,
) -> dict:
    return {
        "type": anomaly_type,
        "severity": severity,
        "message": message,
        "recommended_action": recommended_action,
        "evidence": evidence or {},
    }


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def detect_energy_spike(state) -> list[dict]:
    current_kwh = state.energy.electricity_kwh
    difference_percent = ((current_kwh - BASELINE_ELECTRICITY_KWH) / BASELINE_ELECTRICITY_KWH) * 100

    if current_kwh > BASELINE_ELECTRICITY_KWH:
        return [
            create_anomaly(
                "energy_spike",
                "high",
                "Current electricity use is above the Layer 1 baseline.",
                "Review recent control actions and investigate unexpected loads.",
                {
                    "current_kwh": current_kwh,
                    "baseline_kwh": BASELINE_ELECTRICITY_KWH,
                    "difference_percent": difference_percent,
                },
            )
        ]

    if current_kwh >= BASELINE_ELECTRICITY_KWH * 0.95:
        return [
            create_anomaly(
                "inefficient_energy_use",
                "medium",
                "Current electricity use is within 5% of the baseline, leaving little optimization margin.",
                "Review schedules, lighting levels, and HVAC operation for additional savings.",
                {
                    "current_kwh": current_kwh,
                    "baseline_kwh": BASELINE_ELECTRICITY_KWH,
                    "difference_percent": difference_percent,
                },
            )
        ]

    return []


def detect_hvac_abnormality(state) -> list[dict]:
    hvac_ratio = safe_ratio(state.energy.hvac_kwh, state.energy.electricity_kwh)
    evidence = {
        "hvac_kwh": state.energy.hvac_kwh,
        "electricity_kwh": state.energy.electricity_kwh,
        "hvac_ratio": hvac_ratio,
    }

    if hvac_ratio > 0.30:
        return [
            create_anomaly(
                "hvac_abnormal_load",
                "high",
                "HVAC energy share is abnormally high.",
                "Inspect HVAC schedules, setpoints, economizer behavior, and simultaneous heating/cooling risk.",
                evidence,
            )
        ]

    if hvac_ratio > 0.20:
        return [
            create_anomaly(
                "hvac_elevated_load",
                "medium",
                "HVAC energy share is elevated.",
                "Review HVAC operating mode and zone comfort demand.",
                evidence,
            )
        ]

    return []


def detect_lighting_waste(state) -> list[dict]:
    anomalies = []

    for zone in state.zones:
        evidence = {
            "zone_id": zone.zone_id,
            "occupancy_count": zone.occupancy_count,
            "lighting_level_percent": zone.lighting_level_percent,
        }

        if zone.occupancy_count == 0 and zone.lighting_level_percent > 50:
            anomalies.append(
                create_anomaly(
                    "lighting_waste",
                    "medium",
                    f"{zone.zone_id} has lighting on while unoccupied.",
                    "Dim or turn off lights in unoccupied zones.",
                    evidence,
                )
            )
        elif zone.occupancy_count > 0 and zone.lighting_level_percent > 90:
            anomalies.append(
                create_anomaly(
                    "excessive_lighting",
                    "low",
                    f"{zone.zone_id} lighting level is high while occupied.",
                    "Check daylight availability and reduce lighting level if comfort allows.",
                    evidence,
                )
            )

    return anomalies


def detect_air_quality_issue(state) -> list[dict]:
    anomalies = []

    for zone in state.zones:
        if zone.occupancy_count <= 0 or zone.co2_ppm <= 1000:
            continue

        severity = "high" if zone.co2_ppm > 1200 else "medium"
        anomaly_type = "poor_iaq" if zone.co2_ppm > 1200 else "elevated_co2"
        anomalies.append(
            create_anomaly(
                anomaly_type,
                severity,
                f"{zone.zone_id} CO2 is elevated while occupied.",
                "Increase ventilation or investigate occupancy and air distribution in the zone.",
                {
                    "zone_id": zone.zone_id,
                    "co2_ppm": zone.co2_ppm,
                    "occupancy_count": zone.occupancy_count,
                },
            )
        )

    return anomalies


def detect_comfort_anomaly(state) -> list[dict]:
    evidence = {
        "comfort_status": state.comfort.status,
        "comfort_score": state.comfort.comfort_score,
        "comfort_violation_minutes": state.comfort.comfort_violation_minutes,
        "violations": state.comfort.violations,
    }

    if state.comfort.status == "Unsafe":
        return [
            create_anomaly(
                "comfort_risk",
                "critical",
                "Building comfort status is unsafe.",
                "Override optimization and restore comfort-safe conditions immediately.",
                evidence,
            )
        ]

    if state.comfort.status == "Warning":
        return [
            create_anomaly(
                "comfort_warning",
                "medium",
                "Building comfort has active warnings.",
                "Review zone temperature, CO2, and occupied comfort violations.",
                evidence,
            )
        ]

    return []


def detect_water_leak_placeholder(state) -> list[dict]:
    """Future water leak detection will use water-flow telemetry when available."""
    water_flow_lpm = None

    if isinstance(state, dict):
        water_flow_lpm = state.get("water_flow_lpm")
        total_occupancy = state.get("occupancy", {}).get("total_occupancy", 0)
    else:
        water_flow_lpm = getattr(state, "water_flow_lpm", None)
        total_occupancy = state.occupancy.total_occupancy

    if water_flow_lpm is not None and water_flow_lpm > 0 and total_occupancy == 0:
        return [
            create_anomaly(
                "water_leak_suspected",
                "medium",
                "Water flow is present while the building appears unoccupied.",
                "Inspect plumbing fixtures and future water telemetry feeds.",
                {
                    "water_flow_lpm": water_flow_lpm,
                    "total_occupancy": total_occupancy,
                },
            )
        ]

    return []


def detect_equipment_degradation_placeholder(state) -> list[dict]:
    equipment_ratio = safe_ratio(state.energy.equipment_kwh, state.energy.electricity_kwh)

    if equipment_ratio > 0.40:
        return [
            create_anomaly(
                "equipment_energy_drift",
                "medium",
                "Equipment energy share is higher than expected.",
                "Inspect plug loads, equipment schedules, and future equipment telemetry.",
                {
                    "equipment_kwh": state.energy.equipment_kwh,
                    "electricity_kwh": state.energy.electricity_kwh,
                    "equipment_ratio": equipment_ratio,
                },
            )
        ]

    return []


def detect_anomalies(state) -> list[dict]:
    if state.comfort.source != "phase_2_3_comfort_engine":
        state = apply_comfort_engine(state)

    anomalies = []
    anomalies.extend(detect_energy_spike(state))
    anomalies.extend(detect_hvac_abnormality(state))
    anomalies.extend(detect_lighting_waste(state))
    anomalies.extend(detect_air_quality_issue(state))
    anomalies.extend(detect_comfort_anomaly(state))
    anomalies.extend(detect_water_leak_placeholder(state))
    anomalies.extend(detect_equipment_degradation_placeholder(state))

    return sorted(
        anomalies,
        key=lambda anomaly: SEVERITY_PRIORITY.get(anomaly["severity"], 0),
        reverse=True,
    )


def highest_severity(anomalies: list[dict]) -> str:
    if not anomalies:
        return "none"

    return max(
        (anomaly["severity"] for anomaly in anomalies),
        key=lambda severity: SEVERITY_PRIORITY.get(severity, 0),
    )


def get_latest_anomalies() -> dict:
    state = extract_building_state_from_latest_run()
    state = apply_comfort_engine(state)
    anomalies = detect_anomalies(state)

    return {
        "anomaly_count": len(anomalies),
        "highest_severity": highest_severity(anomalies),
        "anomalies": anomalies,
    }
