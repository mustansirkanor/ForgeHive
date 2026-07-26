from backend.app.cognitive.natural_language_operator import run_natural_language_operator


def get_layer4_demo_scenarios() -> list[dict]:
    return [
        {
            "scenario_id": "empty_room_energy",
            "prompt": "The meeting room is empty now. Save energy but keep comfort safe.",
        },
        {
            "scenario_id": "high_co2_iaq",
            "prompt": "CO2 is high in Zone 2. Improve air quality.",
        },
        {
            "scenario_id": "carbon_reduction",
            "prompt": "Grid carbon intensity is high today. Reduce emissions.",
        },
        {
            "scenario_id": "comfort_hot_office",
            "prompt": "People are feeling too hot in the office.",
        },
        {
            "scenario_id": "hvac_energy_spike",
            "prompt": "There is an abnormal HVAC energy spike.",
        },
        {
            "scenario_id": "explain_plan",
            "prompt": "Why did ForgeHive choose this plan?",
        },
    ]


def run_layer4_demo_scenarios() -> dict:
    scenarios = get_layer4_demo_scenarios()
    outputs = []
    for scenario in scenarios:
        output = run_natural_language_operator(
            scenario["prompt"],
            {"scenario_id": scenario["scenario_id"]},
        )
        outputs.append(
            {
                "scenario": scenario,
                "intent": output.get("intent", {}),
                "candidate_count": output.get("candidate_count", 0),
                "selected_provider": output.get("llm_provider_trace", {}).get("selected_provider"),
                "execution_enabled": output.get("execution_enabled"),
                "reasoning_only": output.get("reasoning_only"),
                "explanation": output.get("explanation", ""),
                "operator_output": output,
            }
        )

    return {
        "project": {"name": "ForgeHive", "layer": "Layer 4", "phase": "Phase 4.6"},
        "scenario_count": len(outputs),
        "outputs": outputs,
    }
