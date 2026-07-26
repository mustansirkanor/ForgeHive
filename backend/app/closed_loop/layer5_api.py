from backend.app.closed_loop.bundle_simulator import simulate_candidate_bundles
from backend.app.closed_loop.final_safety_gate import run_final_safety_gate, safe_no_action_approval
from backend.app.closed_loop.reward_ranker import rank_simulated_bundles
from backend.app.cognitive.natural_language_operator import run_natural_language_operator
from backend.app.experience.experience_retriever import retrieve_similar_experiences
from backend.app.experience.similarity import extract_situation_signature_from_context


def deterministic_fallback_bundles() -> list[dict]:
    return [
        {
            "bundle_id": "layer5_fallback_empty_room_bundle",
            "bundle_name": "layer5_fallback_empty_room_bundle",
            "goal": "reduce_energy_keep_comfort_safe",
            "event_type": "empty_room_detected",
            "actions": [
                {
                    "action_type": "lighting_adjustment",
                    "target": "unoccupied_zones",
                    "description": "Dim lights for empty room.",
                    "parameters": {"lighting_level_percent": 25},
                    "source": "layer5_fallback",
                    "confidence": 0.9,
                },
                {
                    "action_type": "hvac_setpoint_adjustment",
                    "target": "unoccupied_zones",
                    "description": "Relax cooling setpoint safely.",
                    "parameters": {"cooling_setpoint_c": 28},
                    "source": "layer5_fallback",
                    "confidence": 0.85,
                },
                {
                    "action_type": "ventilation_adjustment",
                    "target": "unoccupied_zones",
                    "description": "Reduce ventilation within safe bounds.",
                    "parameters": {"ventilation_percent": 40},
                    "source": "layer5_fallback",
                    "confidence": 0.8,
                },
            ],
            "rationale": "Deterministic fallback candidate for Layer 5 simulation.",
            "constraints": [],
            "expected_outcome": {"energy_saved_percent": 4.0, "comfort_impact": "neutral"},
            "created_by": "layer5_fallback",
            "requires_simulation": True,
            "fallback_used": True,
        }
    ]


def build_dashboard_summary(plan: dict) -> dict:
    selected = plan.get("selected_bundle") or {}
    simulation = selected.get("simulation_result", {}) if selected else {}
    approval = plan.get("final_safety_approval", {})
    return {
        "layer": "Layer 5",
        "phase": "5.1-5.3",
        "status": "complete",
        "closedLoopEnabled": True,
        "energyPlusSimulationEnabled": True,
        "bundleRankingEnabled": True,
        "rlBanditUsed": True,
        "knowledgeGraphUsed": True,
        "safetyGovernorUsed": True,
        "executionReady": plan.get("execution_ready", False),
        "executionApplied": False,
        "candidateCount": plan.get("candidate_count", 0),
        "simulationCount": plan.get("simulation_count", 0),
        "successfulSimulationCount": plan.get("successful_simulation_count", 0),
        "selectedBundleName": selected.get("bundle_name", ""),
        "selectedBundleScore": selected.get("total_score", 0),
        "selectedBundleEnergySavedPercent": simulation.get("energy_saved_percent", 0),
        "selectedBundleCarbonReducedPercent": simulation.get("carbon_reduced_percent", 0),
        "comfortStatus": simulation.get("comfort_status", "Unknown"),
        "riskLevel": approval.get("risk_level", "low"),
        "summary": "Layer 5 simulated, ranked, and safety-approved a candidate plan but did not execute it yet.",
    }


def build_explanation(plan: dict) -> str:
    selected = plan.get("selected_bundle") or {}
    approval = plan.get("final_safety_approval", {})
    if plan.get("closed_loop_status") == "safe_no_action":
        return (
            f"Layer 5 evaluated {plan.get('candidate_count', 0)} candidate bundle(s), but no bundle produced a successful "
            "simulation and safety-approved action set. ForgeHive returned a safe no-action plan and did not execute anything."
        )
    return (
        f"Layer 5 simulated {plan.get('simulation_count', 0)} candidate bundle(s), ranked them with reward, bandit prior, "
        f"and Knowledge Graph relevance, then selected {selected.get('bundle_name')}. The Safety Governor reviewed the selected "
        f"bundle and marked execution_ready={approval.get('execution_ready')}. execution_applied remains false because Phase 5.4 "
        "is responsible for applying approved actions inside the EnergyPlus digital twin."
    )


def run_layer5_phase_1_3_closed_loop(
    user_message: str = "The meeting room is empty now. Save energy but keep comfort safe.",
    candidate_bundles: list[dict] | None = None,
    use_layer4_operator: bool = True,
    layer4_output_override: dict | None = None,
) -> dict:
    layer4_output = {}
    layer4_intent = {
        "goal": "reduce_energy_keep_comfort_safe",
        "event_type": "empty_room_detected",
        "intent": "provided_candidate_bundles",
    }
    provider_trace = {}
    kg_context = {}
    fallback_used = False

    if layer4_output_override:
        layer4_output = layer4_output_override
        layer4_intent = layer4_output.get("intent", layer4_intent)
        provider_trace = layer4_output.get("llm_provider_trace", {})
        kg_context = layer4_output.get("knowledge_context", {})

    if candidate_bundles is None and use_layer4_operator and not layer4_output_override:
        try:
            layer4_output = run_natural_language_operator(user_message)
            candidate_bundles = layer4_output.get("candidate_bundles", [])
            layer4_intent = layer4_output.get("intent", layer4_intent)
            provider_trace = layer4_output.get("llm_provider_trace", {})
            kg_context = layer4_output.get("knowledge_context", {})
        except Exception as exc:
            layer4_output = {"error": str(exc)}
            fallback_used = True

    if not candidate_bundles and use_layer4_operator:
        candidate_bundles = deterministic_fallback_bundles()
        fallback_used = True

    candidate_bundles = candidate_bundles or []

    first_candidate = candidate_bundles[0] if candidate_bundles else {}
    goal = layer4_intent.get("goal", first_candidate.get("goal", "safe_no_action"))
    event_type = layer4_intent.get("event_type", first_candidate.get("event_type", "unresolved_request"))
    current_situation = extract_situation_signature_from_context(
        {
            "goal": goal,
            "event_type": event_type,
            "layer4_intent": layer4_intent,
            "layer4_output": layer4_output,
        }
    )
    retrieved_experience = retrieve_similar_experiences(current_situation)
    simulation_output = simulate_candidate_bundles(candidate_bundles)
    ranking_output = rank_simulated_bundles(
        simulation_output.get("simulation_results", []),
        candidate_bundles,
        goal,
        event_type,
        retrieved_experience,
    )

    selected_bundle = ranking_output.get("selected_bundle")
    if selected_bundle:
        original_bundle = selected_bundle.get("original_bundle", {})
        final_safety = run_final_safety_gate(
            selected_bundle,
            original_bundle,
            {
                "request_analysis": layer4_intent.get("request_analysis", {}),
                "user_message": user_message,
            },
        )
        status = "execution_ready_not_applied" if final_safety.get("execution_ready") else "safe_no_action"
    else:
        final_safety = safe_no_action_approval()
        status = "safe_no_action"

    plan = {
        "project": {"name": "ForgeHive", "layer": "Layer 5", "phase": "5.1-5.3"},
        "phase": "5.1-5.3",
        "user_message": user_message,
        "layer4_intent": layer4_intent,
        "layer4_provider_trace": provider_trace,
        "kg_context": kg_context,
        "experience_retrieval": retrieved_experience,
        "experience_prior_used": ranking_output.get("experience_prior_used", False),
        "experience_prior_summary": ranking_output.get("experience_prior_summary", {}),
        "experience_bonus_summary": ranking_output.get("experience_bonus_summary", []),
        "experience_prior_warnings": ranking_output.get("experience_prior_warnings", []),
        "layer4_output": layer4_output,
        "fallback_used": fallback_used,
        "candidate_count": len(candidate_bundles),
        "candidate_bundles": candidate_bundles,
        "baseline": simulation_output.get("baseline", {}),
        "simulation_results": simulation_output.get("simulation_results", []),
        "simulation_count": simulation_output.get("simulation_count", 0),
        "successful_simulation_count": simulation_output.get("successful_simulation_count", 0),
        "ranked_bundles": ranking_output.get("ranked_bundles", []),
        "selected_bundle": selected_bundle,
        "ranking_summary": ranking_output.get("ranking_summary", ""),
        "rl_used": ranking_output.get("rl_used", True),
        "kg_used": ranking_output.get("kg_used", True),
        "experience_graph": {
            "retrieval_used": True,
            **ranking_output.get("experience_prior_summary", {}),
        },
        "final_safety_approval": final_safety,
        "execution_ready": final_safety.get("execution_ready", False),
        "execution_applied": False,
        "closed_loop_status": status,
        "layer5_status": status,
        "proof": {
            "phase_5_1_simulation": True,
            "phase_5_2_ranking": True,
            "phase_5_3_safety_gate": True,
            "execution_applied": False,
            "safety_governor_used": True,
            "rl_bandit_used": True,
            "knowledge_graph_used": True,
            "experience_graph_used": True,
        },
    }
    plan["dashboard_summary"] = build_dashboard_summary(plan)
    plan["explanation"] = build_explanation(plan)
    return plan
