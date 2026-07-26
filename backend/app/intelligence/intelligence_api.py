import json
from pathlib import Path

from backend.app.intelligence.anomaly_detector import detect_anomalies
from backend.app.intelligence.building_score import calculate_building_intelligence_score
from backend.app.intelligence.comfort_engine import apply_comfort_engine, comfort_summary_dict
from backend.app.intelligence.memory_engine import summarize_memory
from backend.app.intelligence.schemas import to_dict, validate_building_state
from backend.app.intelligence.state_extractor import extract_building_state_from_latest_run


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "layer_2_intelligence"
SEVERITY_PRIORITY = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "none": 0,
}
SOURCE_NOTES = [
    "Energy and carbon are sourced from Layer 1 EnergyPlus comparison.",
    "Zone-level telemetry is currently deterministic demo-derived placeholder data until deeper EnergyPlus time-series extraction is added.",
    "Comfort is computed by the Phase 2.3 comfort engine.",
]


def build_anomaly_summary(anomalies: list[dict]) -> dict:
    if not anomalies:
        highest = "none"
    else:
        highest = max(
            (anomaly.get("severity", "none") for anomaly in anomalies),
            key=lambda severity: SEVERITY_PRIORITY.get(severity, 0),
        )

    return {
        "anomaly_count": len(anomalies),
        "highest_severity": highest,
        "anomalies": anomalies,
    }


def get_building_intelligence_package() -> dict:
    state = extract_building_state_from_latest_run()
    state = apply_comfort_engine(state)
    validation = validate_building_state(state)
    score = calculate_building_intelligence_score(state)
    anomalies = detect_anomalies(state)
    memory_summary = summarize_memory()

    return {
        "project": {
            "name": "ForgeHive",
            "layer": "Layer 2",
            "phase": "Phase 2.7",
            "description": "Unified building intelligence package",
        },
        "building_state": to_dict(state),
        "comfort": comfort_summary_dict(state),
        "score": score,
        "anomalies": build_anomaly_summary(anomalies),
        "memory_summary": memory_summary,
        "validation": validation,
        "source_notes": SOURCE_NOTES,
    }


def get_dashboard_ready_intelligence() -> dict:
    package = get_building_intelligence_package()
    building_state = package["building_state"]
    score = package["score"]
    comfort = package["comfort"]
    anomalies = package["anomalies"]
    best_strategy = package["memory_summary"].get("best_strategy", {})

    return {
        "buildingId": building_state.get("building_id", ""),
        "timestamp": building_state.get("timestamp", ""),
        "overallScore": score.get("overall", 0),
        "grade": score.get("grade", ""),
        "comfortStatus": comfort.get("status", ""),
        "comfortScore": comfort.get("comfort_score", 0),
        "energyEfficiency": score.get("energy_efficiency", 0),
        "carbonOptimization": score.get("carbon_optimization", 0),
        "anomalyCount": anomalies.get("anomaly_count", 0),
        "highestAnomalySeverity": anomalies.get("highest_severity", "none"),
        "bestStrategy": best_strategy.get("strategy", "") if best_strategy.get("available") else "",
        "summary": score.get("summary", ""),
    }


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def save_intelligence_package(output_dir: Path | None = None) -> dict:
    output_path = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    output_path.mkdir(parents=True, exist_ok=True)

    package_file = output_path / "building_intelligence_package.json"
    dashboard_file = output_path / "dashboard_intelligence.json"

    save_json(package_file, get_building_intelligence_package())
    save_json(dashboard_file, get_dashboard_ready_intelligence())

    return {
        "output_dir": str(output_path),
        "generated_files": {
            "building_intelligence_package": str(package_file),
            "dashboard_intelligence": str(dashboard_file),
        },
    }
