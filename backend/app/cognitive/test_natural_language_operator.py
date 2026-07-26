import json
import os
from pathlib import Path

from backend.app.cognitive.demo_scenarios import get_layer4_demo_scenarios
from backend.app.cognitive.layer4_artifacts import export_layer4_cognitive_artifacts
from backend.app.cognitive.natural_language_operator import run_natural_language_operator
from backend.app.cognitive.operator_intents import classify_operator_intent


def set_env(updates: dict) -> dict:
    original = {}
    for key, value in updates.items():
        original[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return original


def restore_env(original: dict) -> None:
    for key, value in original.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def assert_reasoning_only(output: dict) -> None:
    assert output["execution_enabled"] is False
    assert output["execution_allowed"] is False
    assert output["reasoning_only"] is True
    assert output["layer5_handoff"]


if __name__ == "__main__":
    original = set_env({"FORGEHIVE_LLM_MODE": "mock"})
    try:
        empty_output = run_natural_language_operator("The meeting room is empty now. Save energy but keep comfort safe.")
        co2_output = run_natural_language_operator("CO2 is high in Zone 2. Improve air quality.")
        carbon_output = run_natural_language_operator("Grid carbon intensity is high today. Reduce emissions.")
        comfort_output = run_natural_language_operator("People are feeling too hot in the office.")
        status_output = run_natural_language_operator("What is the building health status and score?")
        explain_output = run_natural_language_operator("Why did ForgeHive choose this plan?")
        safety_output = run_natural_language_operator("Is this safe? Show guardrails and risk.")

        assert classify_operator_intent("The meeting room is empty now.")["intent"] == "empty_room_energy_saving"
        assert empty_output["intent"]["intent"] == "empty_room_energy_saving"
        assert co2_output["intent"]["intent"] == "iaq_improvement"
        assert carbon_output["intent"]["intent"] == "carbon_reduction"
        assert comfort_output["intent"]["intent"] == "comfort_protection"
        assert status_output["intent"]["intent"] == "general_building_status"
        assert explain_output["intent"]["intent"] == "explain_decision"
        assert explain_output["explanation"]
        assert safety_output["intent"]["intent"] == "safety_review"
        assert safety_output["safety_guardrails"]

        outputs = [
            empty_output,
            co2_output,
            carbon_output,
            comfort_output,
            status_output,
            explain_output,
            safety_output,
        ]
        for output in outputs:
            assert_reasoning_only(output)
            assert output["project"]["phase"] == "Phase 4.6"

        for output in [empty_output, co2_output, carbon_output, comfort_output]:
            assert output["candidate_count"] > 0
            assert output["llm_provider_trace"]["selected_provider"] == "mock"

        scenarios = get_layer4_demo_scenarios()
        assert len(scenarios) >= 6

        artifact_result = export_layer4_cognitive_artifacts()
        generated_files = artifact_result["generated_files"]
        for path in generated_files.values():
            assert Path(path).exists(), f"Missing artifact: {path}"

        print(json.dumps({
            "empty_intent": empty_output["intent"],
            "co2_intent": co2_output["intent"],
            "carbon_intent": carbon_output["intent"],
            "comfort_intent": comfort_output["intent"],
            "status_intent": status_output["intent"],
            "artifact_files": generated_files,
        }, indent=2))
    finally:
        restore_env(original)

    print("\nPhase 4.6 test passed: Natural language building operator is working.")
