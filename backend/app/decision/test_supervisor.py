import copy
import json

from backend.app.decision.supervisor import run_multi_agent_supervisor
from backend.app.intelligence.intelligence_api import get_building_intelligence_package


def ranked_includes_agent(result: dict, agent_name: str) -> bool:
    return any(
        item.get("agent_name") == agent_name
        for item in result.get("ranked_recommendations", [])
    )


def build_artificial_intelligence_package() -> dict:
    intelligence = copy.deepcopy(get_building_intelligence_package())
    intelligence["comfort"]["status"] = "Warning"
    intelligence["comfort"]["comfort_score"] = 78.0
    intelligence["comfort"]["violations"] = ["SPACE2-1 CO2 is elevated while occupied."]
    intelligence["anomalies"] = {
        "anomaly_count": 1,
        "highest_severity": "high",
        "anomalies": [
            {
                "type": "poor_iaq",
                "severity": "high",
                "message": "SPACE2-1 CO2 is elevated while occupied.",
                "recommended_action": "Increase ventilation.",
                "evidence": {
                    "zone_id": "SPACE2-1",
                    "co2_ppm": 1300,
                    "occupancy_count": 3,
                },
            }
        ],
    }
    return intelligence


if __name__ == "__main__":
    energy_result = run_multi_agent_supervisor(goal="reduce_energy_keep_comfort_safe")
    print(json.dumps(energy_result, indent=2))

    carbon_result = run_multi_agent_supervisor(goal="reduce_carbon")
    print(json.dumps(carbon_result, indent=2))

    artificial_intelligence = build_artificial_intelligence_package()
    anomaly_result = run_multi_agent_supervisor(
        goal="fix_anomalies",
        intelligence=artificial_intelligence,
    )
    print(json.dumps(anomaly_result, indent=2))

    anomaly_selected_type = anomaly_result["selected_recommendation"]["recommended_action"]["action_type"]
    anomaly_top_agents = [
        item["agent_name"]
        for item in anomaly_result["ranked_recommendations"][:2]
    ]

    passed = (
        len(energy_result["agents_consulted"]) >= 4
        and len(energy_result["recommendations"]) >= 4
        and bool(energy_result["selected_recommendation"])
        and bool(energy_result["safety_decision"])
        and energy_result["status"] in ["approved", "rejected"]
        and (energy_result["status"] == "rejected" or energy_result["final_action"] is not None)
        and bool(energy_result["safety_decision"].get("checked_constraints"))
        and ranked_includes_agent(carbon_result, "carbon_agent")
        and ranked_includes_agent(anomaly_result, "anomaly_agent")
        and (
            anomaly_selected_type in ["anomaly_response", "ventilation_adjustment"]
            or "anomaly_agent" in anomaly_top_agents
            or "comfort_agent" in anomaly_top_agents
        )
        and bool(anomaly_result["safety_decision"])
    )

    if passed:
        print("\nPhase 3.2 and 3.3 test passed: Domain agents and multi-agent supervisor are working.")
    else:
        print("\nPhase 3.2 and 3.3 test failed: Domain agents or supervisor did not meet expected checks.")
        raise SystemExit(1)
