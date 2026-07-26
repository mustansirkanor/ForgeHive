import json

from backend.app.intelligence.memory_engine import (
    add_memory_entry,
    create_memory_entry,
    ensure_memory_store,
    get_best_performing_strategy,
    get_recent_memory,
    load_memory,
    record_latest_layer1_strategy_result,
    summarize_memory,
)


def entries_have_required_fields(entries: list[dict]) -> bool:
    required_fields = ["id", "timestamp", "strategy", "action_taken", "comfort_status"]
    return all(
        all(field in entry for field in required_fields)
        for entry in entries
    )


if __name__ == "__main__":
    memory_file = ensure_memory_store()
    load_memory()

    latest_entry = record_latest_layer1_strategy_result()
    artificial_entry = create_memory_entry(
        strategy="comfort_mode",
        action_taken="Maintained occupied-zone comfort during high CO2 condition.",
        predicted_energy_saved_percent=2.0,
        actual_energy_saved_percent=1.5,
        carbon_reduced_percent=1.2,
        comfort_status="Safe",
        anomalies_detected=1,
        lesson="Comfort mode protects IAQ and comfort during abnormal conditions.",
    )
    saved_artificial_entry = add_memory_entry(artificial_entry)

    memory = load_memory()
    recent_memory = get_recent_memory()
    best_strategy = get_best_performing_strategy()
    summary = summarize_memory()

    print(json.dumps({"saved_entries": [latest_entry, saved_artificial_entry]}, indent=2))
    print(json.dumps({"recent_memory": recent_memory}, indent=2))
    print(json.dumps({"best_strategy": best_strategy}, indent=2))
    print(json.dumps({"memory_summary": summary}, indent=2))

    passed = (
        memory_file.exists()
        and len(memory["entries"]) >= 2
        and len(recent_memory) >= 1
        and best_strategy["available"] is True
        and entries_have_required_fields(memory["entries"])
    )

    if passed:
        print("\nPhase 2.6 test passed: Building memory engine is working.")
    else:
        print("\nPhase 2.6 test failed: Building memory engine did not meet expected checks.")
        raise SystemExit(1)
