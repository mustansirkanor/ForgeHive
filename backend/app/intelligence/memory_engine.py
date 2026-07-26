import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.app.energyplus.comparison_api import get_baseline_vs_forgehive_comparison
from backend.app.intelligence.anomaly_detector import get_latest_anomalies


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_memory_file_path() -> Path:
    return PROJECT_ROOT / "data" / "memory" / "building_memory.json"


def ensure_memory_store() -> Path:
    memory_file = get_memory_file_path()
    memory_file.parent.mkdir(parents=True, exist_ok=True)

    if not memory_file.exists():
        memory_file.write_text(json.dumps({"entries": []}, indent=2))

    return memory_file


def load_memory() -> dict:
    memory_file = ensure_memory_store()

    try:
        with memory_file.open(errors="ignore") as file:
            memory = json.load(file)
    except json.JSONDecodeError:
        bad_file = memory_file.with_suffix(".invalid.json")
        try:
            memory_file.replace(bad_file)
        except OSError:
            pass
        memory = {"entries": []}
        save_memory(memory)
    except OSError:
        memory = {"entries": []}

    if not isinstance(memory, dict):
        memory = {"entries": []}

    if not isinstance(memory.get("entries"), list):
        memory["entries"] = []

    return memory


def save_memory(memory: dict) -> None:
    memory_file = ensure_memory_store()

    if not isinstance(memory, dict):
        memory = {"entries": []}

    if not isinstance(memory.get("entries"), list):
        memory["entries"] = []

    memory_file.write_text(json.dumps(memory, indent=2))


def generate_lesson(
    strategy: str,
    actual_energy_saved_percent: float | None,
    comfort_status: str,
) -> str:
    if actual_energy_saved_percent is None:
        return f"Strategy {strategy} is pending measured feedback."

    if comfort_status == "Safe":
        return f"Strategy {strategy} performed safely with {actual_energy_saved_percent:.2f}% energy savings."

    return f"Strategy {strategy} requires review because comfort status was {comfort_status}."


def create_memory_entry(
    strategy: str,
    action_taken: str,
    predicted_energy_saved_percent: float,
    actual_energy_saved_percent: float | None,
    comfort_status: str,
    carbon_reduced_percent: float | None = None,
    anomalies_detected: int = 0,
    lesson: str | None = None,
    metadata: dict | None = None,
) -> dict:
    entry_lesson = lesson or generate_lesson(
        strategy,
        actual_energy_saved_percent,
        comfort_status,
    )

    return {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy": strategy,
        "action_taken": action_taken,
        "predicted_energy_saved_percent": predicted_energy_saved_percent,
        "actual_energy_saved_percent": actual_energy_saved_percent,
        "carbon_reduced_percent": carbon_reduced_percent,
        "comfort_status": comfort_status,
        "anomalies_detected": anomalies_detected,
        "lesson": entry_lesson,
        "metadata": metadata or {},
    }


def add_memory_entry(entry: dict) -> dict:
    memory = load_memory()
    memory["entries"].append(entry)
    save_memory(memory)
    return entry


def record_latest_layer1_strategy_result() -> dict:
    comparison = get_baseline_vs_forgehive_comparison()
    anomalies = get_latest_anomalies()

    if comparison.get("error"):
        entry = create_memory_entry(
            strategy="eco_mode",
            action_taken="Layer 1 optimized strategy result could not be loaded.",
            predicted_energy_saved_percent=0.0,
            actual_energy_saved_percent=None,
            carbon_reduced_percent=None,
            comfort_status="Unknown",
            anomalies_detected=anomalies.get("anomaly_count", 0),
            metadata={"comparison_error": comparison.get("message", "")},
        )
        return add_memory_entry(entry)

    impact = comparison.get("impact", {})
    metadata = comparison.get("metadata", {})
    strategy_name = metadata.get("strategy_name") or "eco_mode"

    entry = create_memory_entry(
        strategy=strategy_name,
        action_taken=metadata.get("verdict") or "Layer 1 optimized strategy applied.",
        predicted_energy_saved_percent=float(impact.get("energy_saved_percent", 0.0)),
        actual_energy_saved_percent=float(impact.get("energy_saved_percent", 0.0)),
        carbon_reduced_percent=float(impact.get("carbon_reduced_percent", 0.0)),
        comfort_status=impact.get("comfort_status") or "Safe",
        anomalies_detected=anomalies.get("anomaly_count", 0),
        metadata={
            "baseline_run_dir": metadata.get("baseline_run_dir", ""),
            "optimized_run_dir": metadata.get("optimized_run_dir", ""),
            "source": metadata.get("source", "latest_comparison_json"),
            "highest_anomaly_severity": anomalies.get("highest_severity", "none"),
        },
    )
    return add_memory_entry(entry)


def get_recent_memory(limit: int = 5) -> list[dict]:
    memory = load_memory()
    entries = memory["entries"]
    return list(reversed(entries))[:limit]


def get_best_performing_strategy() -> dict:
    memory = load_memory()
    measured_entries = [
        entry
        for entry in memory["entries"]
        if entry.get("actual_energy_saved_percent") is not None
    ]

    if not measured_entries:
        return {
            "available": False,
            "strategy": "",
            "actual_energy_saved_percent": None,
            "comfort_status": "",
            "lesson": "",
            "entry": {},
        }

    safe_entries = [
        entry
        for entry in measured_entries
        if entry.get("comfort_status") == "Safe"
    ]
    candidates = safe_entries or measured_entries
    best_entry = max(candidates, key=lambda entry: entry.get("actual_energy_saved_percent", 0))

    return {
        "available": True,
        "strategy": best_entry.get("strategy", ""),
        "actual_energy_saved_percent": best_entry.get("actual_energy_saved_percent"),
        "comfort_status": best_entry.get("comfort_status", ""),
        "lesson": best_entry.get("lesson", ""),
        "entry": best_entry,
    }


def summarize_memory() -> dict:
    memory = load_memory()
    return {
        "total_entries": len(memory["entries"]),
        "recent_entries": get_recent_memory(),
        "best_strategy": get_best_performing_strategy(),
    }
