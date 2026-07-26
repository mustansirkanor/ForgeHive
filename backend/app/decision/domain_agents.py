import uuid
from dataclasses import asdict, dataclass

from backend.app.decision.action_schema import ControlAction, to_dict


@dataclass
class AgentRecommendation:
    agent_name: str
    goal: str
    recommended_action: ControlAction
    confidence: float
    rationale: str
    expected_benefits: list[str]
    risks: list[str]
    evidence: dict


def create_action(
    strategy_name: str,
    action_type: str,
    target: str,
    description: str,
    parameters: dict,
    expected_energy_saved_percent: float,
    expected_carbon_reduced_percent: float,
    expected_comfort_impact: str,
    source_agent: str,
    priority: str,
) -> ControlAction:
    return ControlAction(
        action_id=str(uuid.uuid4()),
        strategy_name=strategy_name,
        action_type=action_type,
        target=target,
        description=description,
        parameters=parameters,
        expected_energy_saved_percent=expected_energy_saved_percent,
        expected_carbon_reduced_percent=expected_carbon_reduced_percent,
        expected_comfort_impact=expected_comfort_impact,
        source_agent=source_agent,
        priority=priority,
    )


def recommendation_to_dict(recommendation: AgentRecommendation) -> dict:
    data = asdict(recommendation)
    data["recommended_action"] = to_dict(recommendation.recommended_action)
    return data


def get_anomaly_types(intelligence: dict) -> set[str]:
    return {
        anomaly.get("type", "")
        for anomaly in intelligence.get("anomalies", {}).get("anomalies", [])
    }


class EnergyAgent:
    agent_name = "energy_agent"

    def recommend(self, intelligence: dict, goal: str = "balanced_optimization") -> AgentRecommendation:
        score = intelligence.get("score", {})
        building_state = intelligence.get("building_state", {})
        energy = building_state.get("energy", {})
        anomalies = intelligence.get("anomalies", {})
        anomaly_types = get_anomaly_types(intelligence)
        best_strategy = intelligence.get("memory_summary", {}).get("best_strategy", {})

        expected_savings = 5.0
        if best_strategy.get("available") and best_strategy.get("strategy") == "eco_mode":
            expected_savings = float(best_strategy.get("actual_energy_saved_percent") or expected_savings)

        confidence = 0.65
        if "reduce_energy" in goal or score.get("energy_efficiency", 100) < 90:
            confidence += 0.15
        if best_strategy.get("strategy") == "eco_mode":
            confidence += 0.10
        if "lighting_waste" in anomaly_types:
            confidence += 0.10

        action = create_action(
            strategy_name="eco_mode",
            action_type="lighting_adjustment",
            target="unoccupied_zones",
            description="Reduce lighting in unoccupied zones to lower electricity consumption while preserving comfort.",
            parameters={
                "lighting_level_percent": 25,
                "applies_to_occupied_zones": False,
            },
            expected_energy_saved_percent=expected_savings,
            expected_carbon_reduced_percent=expected_savings,
            expected_comfort_impact="neutral",
            source_agent=self.agent_name,
            priority="medium",
        )

        return AgentRecommendation(
            agent_name=self.agent_name,
            goal=goal,
            recommended_action=action,
            confidence=min(confidence, 0.95),
            rationale="Lighting reduction is the safest near-term energy action because it avoids occupied comfort risk.",
            expected_benefits=[
                "Lower electricity use",
                "Preserve occupied-zone comfort",
                "Reuse the proven Layer 1 eco_mode behavior",
            ],
            risks=[],
            evidence={
                "energy_efficiency": score.get("energy_efficiency"),
                "electricity_kwh": energy.get("electricity_kwh"),
                "anomaly_count": anomalies.get("anomaly_count"),
                "best_strategy": best_strategy.get("strategy"),
            },
        )


class ComfortAgent:
    agent_name = "comfort_agent"

    def recommend(self, intelligence: dict, goal: str = "balanced_optimization") -> AgentRecommendation:
        comfort = intelligence.get("comfort", {})
        occupancy = intelligence.get("building_state", {}).get("occupancy", {})
        status = comfort.get("status", "Safe")
        issue_exists = status in ["Warning", "Unsafe"]

        action = create_action(
            strategy_name="comfort_preserving_mode",
            action_type="strategy_mode",
            target="occupied_zones",
            description="Maintain occupied-zone comfort while allowing only conservative efficiency actions.",
            parameters={
                "max_cooling_setpoint_c": 26,
                "min_lighting_level_percent_occupied": 50,
                "comfort_guard_enabled": True,
            },
            expected_energy_saved_percent=2.0,
            expected_carbon_reduced_percent=2.0,
            expected_comfort_impact="positive",
            source_agent=self.agent_name,
            priority="high" if issue_exists else "medium",
        )

        return AgentRecommendation(
            agent_name=self.agent_name,
            goal=goal,
            recommended_action=action,
            confidence=0.90 if issue_exists else 0.60,
            rationale="Comfort guardrails should remain active before any efficiency or carbon action is executed.",
            expected_benefits=[
                "Maintains occupied-zone comfort",
                "Keeps autonomous decisions inside comfort bounds",
            ],
            risks=[],
            evidence={
                "comfort_status": status,
                "comfort_score": comfort.get("comfort_score"),
                "violations": comfort.get("violations", []),
                "total_occupancy": occupancy.get("total_occupancy"),
            },
        )


class CarbonAgent:
    agent_name = "carbon_agent"

    def recommend(self, intelligence: dict, goal: str = "balanced_optimization") -> AgentRecommendation:
        score = intelligence.get("score", {})
        carbon = intelligence.get("building_state", {}).get("carbon", {})
        reduce_carbon_goal = "reduce_carbon" in goal
        confidence = 0.85 if reduce_carbon_goal else 0.65
        if score.get("carbon_optimization", 100) < 90:
            confidence += 0.10

        action = create_action(
            strategy_name="carbon_aware_mode",
            action_type="carbon_schedule_shift",
            target="whole_building",
            description="Shift flexible HVAC and lighting loads toward lower-carbon operating windows while keeping comfort safe.",
            parameters={
                "preconditioning_enabled": True,
                "avoid_peak_carbon_window": True,
                "comfort_guard_enabled": True,
            },
            expected_energy_saved_percent=3.0,
            expected_carbon_reduced_percent=6.0,
            expected_comfort_impact="neutral",
            source_agent=self.agent_name,
            priority="medium",
        )

        return AgentRecommendation(
            agent_name=self.agent_name,
            goal=goal,
            recommended_action=action,
            confidence=min(confidence, 0.95),
            rationale="Carbon-aware scheduling can reduce emissions without requiring aggressive comfort changes.",
            expected_benefits=[
                "Reduce carbon impact",
                "Keep comfort guard enabled",
                "Shift flexible loads away from high-carbon periods",
            ],
            risks=["Requires future carbon-intensity schedule integration for execution."],
            evidence={
                "carbon_optimization": score.get("carbon_optimization"),
                "grid_intensity_kg_per_kwh": carbon.get("grid_intensity_kg_per_kwh"),
            },
        )


class AnomalyAgent:
    agent_name = "anomaly_agent"

    def recommend(self, intelligence: dict, goal: str = "balanced_optimization") -> AgentRecommendation:
        anomalies = intelligence.get("anomalies", {})
        anomaly_list = anomalies.get("anomalies", [])
        anomaly_count = anomalies.get("anomaly_count", 0)
        selected_anomaly = anomaly_list[0] if anomaly_list else {}
        anomaly_type = selected_anomaly.get("type", "")

        if anomaly_type == "lighting_waste":
            action = create_action(
                "anomaly_lighting_response",
                "lighting_adjustment",
                "unoccupied_zones",
                "Reduce lighting in unoccupied zones flagged by anomaly detection.",
                {"lighting_level_percent": 20, "applies_to_occupied_zones": False},
                4.0,
                4.0,
                "neutral",
                self.agent_name,
                "high",
            )
        elif anomaly_type in ["poor_iaq", "elevated_co2"]:
            action = create_action(
                "iaq_recovery",
                "ventilation_adjustment",
                "occupied_zones",
                "Increase ventilation for occupied zones with elevated CO2.",
                {"ventilation_percent": 60, "applies_to_occupied_zones": True},
                0.0,
                0.0,
                "positive",
                self.agent_name,
                "high",
            )
        elif anomaly_type in ["hvac_abnormal_load", "energy_spike", "equipment_energy_drift"]:
            action = create_action(
                "anomaly_investigation_mode",
                "anomaly_response",
                "whole_building",
                "Hold aggressive optimization and investigate abnormal equipment or energy behavior.",
                {"hold_aggressive_changes": True, "request_operator_review": True},
                0.0,
                0.0,
                "neutral",
                self.agent_name,
                "high",
            )
        else:
            action = create_action(
                "normal_monitoring",
                "anomaly_response",
                "whole_building",
                "No active anomalies detected; continue monitoring and preserve current safe operation.",
                {"continue_monitoring": True, "no_direct_control_change": True},
                0.0,
                0.0,
                "neutral",
                self.agent_name,
                "low",
            )

        return AgentRecommendation(
            agent_name=self.agent_name,
            goal=goal,
            recommended_action=action,
            confidence=0.90 if anomaly_count > 0 else 0.55,
            rationale="Anomaly-aware decisions prioritize operational risk before optimization.",
            expected_benefits=[
                "Respond to active anomalies" if anomaly_count > 0 else "Maintain safe monitoring",
                "Avoid unsafe autonomous control during abnormal conditions",
            ],
            risks=[],
            evidence={
                "anomaly_count": anomaly_count,
                "highest_severity": anomalies.get("highest_severity"),
                "selected_anomaly": selected_anomaly,
            },
        )


def get_all_agent_recommendations(intelligence: dict, goal: str) -> list[AgentRecommendation]:
    agents = [
        EnergyAgent(),
        ComfortAgent(),
        CarbonAgent(),
        AnomalyAgent(),
    ]
    return [agent.recommend(intelligence, goal) for agent in agents]
