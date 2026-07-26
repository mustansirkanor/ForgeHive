import copy
import json

from backend.app.intelligence.anomaly_detector import (
    detect_anomalies,
    get_latest_anomalies,
    highest_severity,
)
from backend.app.intelligence.comfort_engine import apply_comfort_engine
from backend.app.intelligence.state_extractor import extract_building_state_from_latest_run


VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def create_artificial_anomaly_state():
    state = copy.deepcopy(extract_building_state_from_latest_run())

    state.energy.electricity_kwh = 52000.0
    state.energy.hvac_kwh = 18000.0
    state.energy.equipment_kwh = 24000.0

    state.zones[0].occupancy_count = 0
    state.zones[0].lighting_level_percent = 80.0

    state.zones[1].occupancy_count = 3
    state.zones[1].co2_ppm = 1300.0

    state.zones[2].occupancy_count = 4
    state.zones[2].temperature_c = 31.0

    return apply_comfort_engine(state)


def anomalies_have_required_fields(anomalies: list[dict]) -> bool:
    for anomaly in anomalies:
        if not all(key in anomaly for key in ["type", "severity", "message", "recommended_action", "evidence"]):
            return False
        if anomaly["severity"] not in VALID_SEVERITIES:
            return False
    return True


if __name__ == "__main__":
    latest_result = get_latest_anomalies()

    artificial_state = create_artificial_anomaly_state()
    artificial_anomalies = detect_anomalies(artificial_state)
    artificial_result = {
        "anomaly_count": len(artificial_anomalies),
        "highest_severity": highest_severity(artificial_anomalies),
        "anomalies": artificial_anomalies,
    }

    artificial_types = {anomaly["type"] for anomaly in artificial_anomalies}

    print(json.dumps(latest_result, indent=2))
    print(json.dumps(artificial_result, indent=2))

    passed = (
        "anomaly_count" in latest_result
        and len(artificial_types) >= 3
        and anomalies_have_required_fields(artificial_anomalies)
    )

    if passed:
        print("\nPhase 2.5 test passed: Anomaly detection is working.")
    else:
        print("\nPhase 2.5 test failed: Anomaly detection did not meet expected checks.")
        raise SystemExit(1)
