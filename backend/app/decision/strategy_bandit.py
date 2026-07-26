import json
import random
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SUPPORTED_STRATEGIES = [
    "eco_mode",
    "comfort_mode",
    "carbon_aware_mode",
    "balanced_mode",
    "iaq_priority_mode",
    "equipment_protection_mode",
    "anomaly_response_mode",
]


def get_bandit_file_path() -> Path:
    return PROJECT_ROOT / "data" / "decision" / "strategy_bandit.json"


def create_initial_bandit_state() -> dict:
    return {
        "strategies": {
            strategy: {
                "times_selected": 0,
                "total_reward": 0.0,
                "average_reward": 0.0,
            }
            for strategy in SUPPORTED_STRATEGIES
        },
        "history": [],
    }


def ensure_bandit_store() -> Path:
    bandit_file = get_bandit_file_path()
    bandit_file.parent.mkdir(parents=True, exist_ok=True)

    if not bandit_file.exists():
        bandit_file.write_text(json.dumps(create_initial_bandit_state(), indent=2))

    return bandit_file


def normalize_bandit_state(state: dict) -> dict:
    if not isinstance(state, dict):
        state = create_initial_bandit_state()

    if not isinstance(state.get("strategies"), dict):
        state["strategies"] = {}

    for strategy in SUPPORTED_STRATEGIES:
        state["strategies"].setdefault(
            strategy,
            {
                "times_selected": 0,
                "total_reward": 0.0,
                "average_reward": 0.0,
            },
        )

    if not isinstance(state.get("history"), list):
        state["history"] = []

    return state


def load_bandit_state() -> dict:
    bandit_file = ensure_bandit_store()

    try:
        with bandit_file.open(errors="ignore") as file:
            state = json.load(file)
    except json.JSONDecodeError:
        bad_file = bandit_file.with_suffix(".invalid.json")
        try:
            bandit_file.replace(bad_file)
        except OSError:
            pass
        state = create_initial_bandit_state()
        save_bandit_state(state)
    except OSError:
        state = create_initial_bandit_state()

    return normalize_bandit_state(state)


def save_bandit_state(state: dict) -> None:
    bandit_file = ensure_bandit_store()
    bandit_file.write_text(json.dumps(normalize_bandit_state(state), indent=2))


def extract_context_features(intelligence: dict) -> dict:
    score = intelligence.get("score", {})
    comfort = intelligence.get("comfort", {})
    anomalies = intelligence.get("anomalies", {})
    best_strategy = intelligence.get("memory_summary", {}).get("best_strategy", {})

    return {
        "comfort_status": comfort.get("status", "Safe"),
        "overall_score": score.get("overall", 0),
        "energy_efficiency": score.get("energy_efficiency", 0),
        "carbon_optimization": score.get("carbon_optimization", 0),
        "anomaly_count": anomalies.get("anomaly_count", 0),
        "highest_anomaly_severity": anomalies.get("highest_severity", "none"),
        "best_memory_strategy": best_strategy.get("strategy", "") if best_strategy.get("available") else "",
    }


def strategy_scores_from_state(state: dict) -> dict:
    return {
        strategy: values.get("average_reward", 0.0)
        for strategy, values in state.get("strategies", {}).items()
    }


def best_average_reward_strategy(state: dict) -> str:
    scores = strategy_scores_from_state(state)
    return max(scores, key=lambda strategy: scores[strategy])


def choose_strategy_for_context(
    intelligence: dict,
    goal: str = "balanced_optimization",
    exploration_rate: float = 0.0,
) -> dict:
    state = load_bandit_state()
    context = extract_context_features(intelligence)
    scores = strategy_scores_from_state(state)

    if exploration_rate > 0 and random.random() < exploration_rate:
        selected_strategy = random.choice(SUPPORTED_STRATEGIES)
        reason = "Exploration selected a random supported strategy."
    elif "fix_anomalies" in goal and context["anomaly_count"] > 0:
        selected_strategy = "anomaly_response_mode"
        reason = "Goal requests anomaly repair and active anomalies are present."
    elif context["highest_anomaly_severity"] in ["high", "critical"]:
        selected_strategy = "anomaly_response_mode"
        reason = "High or critical anomaly severity requires anomaly response."
    elif context["comfort_status"] in ["Warning", "Unsafe"]:
        selected_strategy = "iaq_priority_mode" if context["anomaly_count"] > 0 else "comfort_mode"
        reason = "Comfort is degraded, so safety and comfort recovery are prioritized."
    elif "reduce_energy" in goal:
        selected_strategy = "eco_mode"
        reason = "Goal requests energy reduction."
    elif "reduce_carbon" in goal:
        selected_strategy = "carbon_aware_mode"
        reason = "Goal requests carbon reduction."
    elif "maintain_comfort" in goal:
        selected_strategy = "comfort_mode"
        reason = "Goal requests comfort maintenance."
    else:
        selected_strategy = best_average_reward_strategy(state)
        reason = "Selected best average reward strategy from bandit state."

        memory_strategy = context.get("best_memory_strategy")
        if memory_strategy and scores.get(memory_strategy, 0.0) == scores.get(selected_strategy, 0.0):
            selected_strategy = memory_strategy
            reason = "Bandit reward tie broken by best memory strategy."

    return {
        "selected_strategy": selected_strategy,
        "selection_reason": reason,
        "context": context,
        "strategy_scores": scores,
        "source": "contextual_bandit",
    }


def calculate_reward(
    energy_saved_percent: float,
    carbon_reduced_percent: float,
    comfort_status: str,
    anomaly_count: int = 0,
    action_approved: bool = True,
) -> float:
    reward = energy_saved_percent + (carbon_reduced_percent * 0.8)

    if comfort_status == "Safe":
        reward += 10
    elif comfort_status == "Warning":
        reward -= 5
    elif comfort_status == "Unsafe":
        reward -= 20

    reward -= anomaly_count * 2

    if not action_approved:
        reward -= 15

    return round(reward, 2)


def update_strategy_reward(
    strategy_name: str,
    reward: float,
    metadata: dict | None = None,
) -> dict:
    state = load_bandit_state()
    strategies = state["strategies"]
    strategies.setdefault(
        strategy_name,
        {
            "times_selected": 0,
            "total_reward": 0.0,
            "average_reward": 0.0,
        },
    )

    strategy_state = strategies[strategy_name]
    strategy_state["times_selected"] += 1
    strategy_state["total_reward"] = round(strategy_state["total_reward"] + reward, 2)
    strategy_state["average_reward"] = round(
        strategy_state["total_reward"] / strategy_state["times_selected"],
        2,
    )

    state["history"].append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy": strategy_name,
            "reward": reward,
            "metadata": metadata or {},
        }
    )

    save_bandit_state(state)
    return strategy_state


def seed_bandit_from_memory() -> dict:
    try:
        from backend.app.intelligence.memory_engine import summarize_memory

        memory_summary = summarize_memory()
    except Exception:
        return load_bandit_state()

    recent_entries = memory_summary.get("recent_entries", [])
    for entry in recent_entries:
        if entry.get("actual_energy_saved_percent") is None:
            continue

        reward = calculate_reward(
            energy_saved_percent=float(entry.get("actual_energy_saved_percent") or 0.0),
            carbon_reduced_percent=float(entry.get("carbon_reduced_percent") or 0.0),
            comfort_status=entry.get("comfort_status", "Safe"),
            anomaly_count=int(entry.get("anomalies_detected") or 0),
            action_approved=True,
        )
        update_strategy_reward(
            entry.get("strategy", "balanced_mode"),
            reward,
            metadata={
                "source": "memory_seed",
                "memory_entry_id": entry.get("id", ""),
            },
        )

    return load_bandit_state()
