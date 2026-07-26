from backend.app.closed_loop.bundle_to_strategy import slugify
from backend.app.closed_loop.reward_ranker import closest_strategy_for_bundle
from backend.app.decision.strategy_bandit import update_strategy_reward


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_expected_vs_actual(plan_5_1_3: dict, execution_result: dict) -> dict:
    selected = plan_5_1_3.get("selected_bundle") or {}
    expected = selected.get("simulation_result") or {}
    expected_energy = safe_float(expected.get("energy_saved_percent"))
    actual_energy = safe_float(execution_result.get("energy_saved_percent"))
    expected_carbon = safe_float(expected.get("carbon_reduced_percent"))
    actual_carbon = safe_float(execution_result.get("carbon_reduced_percent"))
    expected_comfort = expected.get("comfort_status", "Unknown")
    actual_comfort = execution_result.get("comfort_status", "Unknown")
    comfort_regression = expected_comfort == "Safe" and actual_comfort in {"Warning", "Unsafe"}
    execution_success = (
        execution_result.get("execution_status") == "executed"
        and execution_result.get("execution_applied") is True
    )

    return {
        "expected_energy_saved_percent": round(expected_energy, 4),
        "actual_energy_saved_percent": round(actual_energy, 4),
        "expected_carbon_reduced_percent": round(expected_carbon, 4),
        "actual_carbon_reduced_percent": round(actual_carbon, 4),
        "expected_comfort_status": expected_comfort,
        "actual_comfort_status": actual_comfort,
        "delta_energy_saving": round(actual_energy - expected_energy, 4),
        "delta_carbon_reduction": round(actual_carbon - expected_carbon, 4),
        "comfort_regression": comfort_regression,
        "execution_success": execution_success,
    }


def calculate_actual_reward(comparison: dict, execution_result: dict) -> float:
    reward = comparison.get("actual_energy_saved_percent", 0.0)
    reward += comparison.get("actual_carbon_reduced_percent", 0.0) * 0.8

    comfort_status = comparison.get("actual_comfort_status", "Unknown")
    if comfort_status == "Safe":
        reward += 10
    elif comfort_status == "Warning":
        reward -= 10
    elif comfort_status == "Unsafe":
        reward -= 25

    reward -= int(execution_result.get("anomaly_count", 0) or 0) * 3
    if not comparison.get("execution_success"):
        reward -= 20
    if comparison.get("comfort_regression"):
        reward -= 10
    return round(reward, 4)


def generate_self_correction_recommendation(comparison: dict) -> dict:
    recommendations = []
    if not comparison.get("execution_success"):
        recommendations.append("use safe no-action fallback and inspect simulation mapping")
    if comparison.get("delta_energy_saving", 0) < -2:
        recommendations.append("reduce confidence in this bundle and prefer alternative strategy next time")
    if comparison.get("comfort_regression"):
        recommendations.append("tighten comfort guardrails and prefer comfort-preserving bundle")
    if comparison.get("delta_carbon_reduction", 0) < -2:
        recommendations.append("increase carbon-aware scheduling weight")
    if not recommendations:
        recommendations.append("increase confidence in selected strategy")

    return {
        "recommendations": recommendations,
        "summary": "; ".join(recommendations),
        "prediction_matched_actual": (
            comparison.get("execution_success")
            and abs(comparison.get("delta_energy_saving", 0)) <= 2
            and abs(comparison.get("delta_carbon_reduction", 0)) <= 2
            and not comparison.get("comfort_regression")
        ),
    }


def record_memory_update(strategy: str, plan_5_1_3: dict, execution_result: dict, comparison: dict) -> dict:
    try:
        from backend.app.intelligence.memory_engine import add_memory_entry, create_memory_entry

        selected = plan_5_1_3.get("selected_bundle") or {}
        approval = plan_5_1_3.get("final_safety_approval") or {}
        entry = create_memory_entry(
            strategy=strategy,
            action_taken=f"Layer 5 digital twin execution for {selected.get('bundle_name', 'selected_bundle')}.",
            predicted_energy_saved_percent=comparison.get("expected_energy_saved_percent", 0.0),
            actual_energy_saved_percent=comparison.get("actual_energy_saved_percent", 0.0),
            carbon_reduced_percent=comparison.get("actual_carbon_reduced_percent", 0.0),
            comfort_status=comparison.get("actual_comfort_status", "Unknown"),
            anomalies_detected=int(execution_result.get("anomaly_count", 0) or 0),
            metadata={
                "source": "layer5_phase_5_5_feedback",
                "selected_bundle_name": selected.get("bundle_name", ""),
                "approved_action_count": len(approval.get("approved_actions", []) or []),
                "approved_actions": approval.get("approved_actions", []),
                "execution_run_dir": execution_result.get("run_dir", ""),
                "prediction_matched_actual": generate_self_correction_recommendation(comparison).get("prediction_matched_actual"),
            },
        )
        return {"updated": True, "entry": add_memory_entry(entry), "note": "Memory updated from successful digital twin execution."}
    except Exception as exc:
        return {"updated": False, "entry": {}, "note": f"Memory update skipped safely: {exc}"}


def record_kg_update(strategy: str, plan_5_1_3: dict, execution_result: dict, comparison: dict) -> dict:
    try:
        from backend.app.cognitive.knowledge_graph import add_edge, load_knowledge_graph, record_event, save_knowledge_graph

        def ensure_node(node_id: str, node_type: str, label: str, properties: dict | None = None) -> dict:
            graph = load_knowledge_graph()
            if node_id not in graph["nodes"]:
                graph["nodes"][node_id] = {"id": node_id, "type": node_type, "label": label, "properties": properties or {}}
            else:
                graph["nodes"][node_id].setdefault("properties", {})
                graph["nodes"][node_id]["properties"].update(properties or {})
            save_knowledge_graph(graph)
            return graph["nodes"][node_id]

        selected = plan_5_1_3.get("selected_bundle") or {}
        original = selected.get("original_bundle") or {}
        bundle_name = selected.get("bundle_name") or original.get("bundle_name") or "selected_bundle"
        bundle_id = f"bundle:{slugify(bundle_name)}"
        outcome_id = f"outcome:layer5_execution:{slugify(bundle_name)}"
        strategy_id = f"strategy:{strategy}"

        ensure_node(bundle_id, "action_bundle", bundle_name, {"phase": "5.5", "goal": original.get("goal", "")})
        ensure_node(outcome_id, "execution_outcome", f"Outcome for {bundle_name}", comparison)
        ensure_node(strategy_id, "strategy", strategy, {"source": "layer5_feedback"})
        add_edge(bundle_id, "EXECUTED_IN_DIGITAL_TWIN", outcome_id, {"run_dir": execution_result.get("run_dir", "")})
        add_edge(strategy_id, "LEARNED_OUTCOME", outcome_id, {"reward_source": "actual_execution"})
        for action in execution_result.get("approved_actions_executed", []) or []:
            action_id = f"action:{action.get('action_type', 'unknown_action')}"
            ensure_node(action_id, "action", action.get("action_type", "unknown_action"), {})
            add_edge(action_id, "IMPACTED", "outcome:energy_saved", {"energy_saved_percent": comparison.get("actual_energy_saved_percent", 0.0)})
            add_edge(action_id, "IMPACTED", "outcome:carbon_reduced", {"carbon_reduced_percent": comparison.get("actual_carbon_reduced_percent", 0.0)})
            add_edge(action_id, "IMPACTED", "outcome:comfort_safe", {"comfort_status": comparison.get("actual_comfort_status", "Unknown")})
        event = record_event(
            "layer5_digital_twin_execution_learned",
            {
                "strategy": strategy,
                "bundle_name": bundle_name,
                "run_dir": execution_result.get("run_dir", ""),
                "comparison": comparison,
            },
        )
        return {"updated": True, "event": event, "note": "Knowledge Graph updated from successful digital twin execution."}
    except Exception as exc:
        return {"updated": False, "event": {}, "note": f"Knowledge Graph update skipped safely: {exc}"}


def learn_from_execution(plan_5_1_3: dict, execution_result: dict) -> dict:
    selected = plan_5_1_3.get("selected_bundle") or {}
    original_bundle = selected.get("original_bundle") or {}
    strategy = closest_strategy_for_bundle(original_bundle)
    comparison = compute_expected_vs_actual(plan_5_1_3, execution_result)
    actual_reward = calculate_actual_reward(comparison, execution_result)
    self_correction = generate_self_correction_recommendation(comparison)
    notes = []
    bandit_updated = False
    memory_result = {"updated": False, "note": "Memory update skipped because execution did not succeed."}
    kg_result = {"updated": False, "note": "Knowledge Graph update skipped because execution did not succeed."}

    if comparison["execution_success"]:
        try:
            update_strategy_reward(
                strategy,
                actual_reward,
                metadata={
                    "source": "layer5_phase_5_5_feedback",
                    "selected_bundle_name": selected.get("bundle_name", ""),
                    "execution_run_dir": execution_result.get("run_dir", ""),
                    "expected_vs_actual": comparison,
                },
            )
            bandit_updated = True
            notes.append("Bandit updated from successful digital twin execution.")
        except Exception as exc:
            notes.append(f"Bandit update failed safely: {exc}")

        memory_result = record_memory_update(strategy, plan_5_1_3, execution_result, comparison)
        kg_result = record_kg_update(strategy, plan_5_1_3, execution_result, comparison)
    else:
        notes.append("Execution did not succeed; bandit, memory, and KG success learning were skipped.")

    notes.extend([memory_result.get("note", ""), kg_result.get("note", "")])
    learning_status = "updated" if comparison["execution_success"] and (bandit_updated or memory_result["updated"] or kg_result["updated"]) else "skipped"

    return {
        "phase": "5.5",
        "learning_status": learning_status,
        "execution_success": comparison["execution_success"],
        "expected_vs_actual": comparison,
        "actual_reward": actual_reward,
        "bandit_updated": bandit_updated,
        "bandit_strategy": strategy,
        "memory_updated": bool(memory_result["updated"]),
        "knowledge_graph_updated": bool(kg_result["updated"]),
        "self_correction": self_correction,
        "learning_notes": [note for note in notes if note],
        "error": None,
    }
