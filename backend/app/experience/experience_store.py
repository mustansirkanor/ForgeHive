import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPERIENCE_GRAPH_PATH = PROJECT_ROOT / "data" / "experience" / "experience_graph.json"
SECRET_PATTERNS = [
    re.compile(r"OPENROUTER_API_KEY", re.IGNORECASE),
    re.compile(r"sk-or-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_graph() -> dict:
    return {
        "version": "8.0",
        "project": "ForgeHive",
        "episodes": [],
        "strategy_stats": {},
        "failure_patterns": [],
        "last_updated": utc_now_iso(),
    }


def sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, str):
        clean = value
        for pattern in SECRET_PATTERNS:
            clean = pattern.sub("[redacted]", clean)
        return clean[:2000]
    return value


def normalize_graph(data: dict | None) -> dict:
    graph = empty_graph()
    if isinstance(data, dict):
        graph.update(data)
    graph["version"] = "8.0"
    graph["project"] = "ForgeHive"
    graph.setdefault("episodes", [])
    graph.setdefault("strategy_stats", {})
    graph.setdefault("failure_patterns", [])
    graph.setdefault("last_updated", utc_now_iso())
    return graph


def load_experience_graph() -> dict:
    EXPERIENCE_GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not EXPERIENCE_GRAPH_PATH.exists():
        save_experience_graph(empty_graph())
    try:
        return normalize_graph(json.loads(EXPERIENCE_GRAPH_PATH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        graph = empty_graph()
        save_experience_graph(graph)
        return graph


def action_types_from_plan(plan: dict) -> list[str]:
    action_types = list(plan.get("action_types") or [])
    for action in plan.get("actions", []) or []:
        action_type = action.get("action_type") or action.get("actionType")
        if action_type:
            action_types.append(action_type)
    return list(dict.fromkeys(action_types))


def selected_plan_name(episode: dict) -> str:
    selected = episode.get("selected_plan") or {}
    return selected.get("bundle_name") or selected.get("name") or "unknown_strategy"


def selected_candidate(episode: dict) -> dict:
    selected = episode.get("selected_plan") or {}
    selected_name = selected_plan_name(episode)
    for plan in episode.get("candidate_plans", []) or []:
        if plan.get("bundle_name") == selected_name or plan.get("bundle_id") == selected.get("bundle_id"):
            return plan
    return selected


def is_success(episode: dict) -> bool:
    outcome = episode.get("execution_outcome") or {}
    selected = selected_candidate(episode)
    return (
        outcome.get("comfort_status") in {"Safe", "IAQ improved", "Comfort improved", "Lighting dimmed safely"}
        and float(outcome.get("reward") or selected.get("reward") or 0) > 0
        and not bool(selected.get("blocked", False))
    )


def rebuild_strategy_stats(episodes: list[dict]) -> dict:
    buckets: dict[str, dict] = {}
    for episode in episodes:
        strategy = selected_plan_name(episode)
        selected = selected_candidate(episode)
        outcome = episode.get("execution_outcome") or {}
        bucket = buckets.setdefault(
            strategy,
            {
                "uses": 0,
                "successes": 0,
                "failures": 0,
                "reward_total": 0.0,
                "energy_total": 0.0,
                "comfort_safe_count": 0,
            },
        )
        reward = float(outcome.get("reward") if outcome.get("reward") is not None else selected.get("reward") or 0)
        energy = float(outcome.get("energy_saved_percent") if outcome.get("energy_saved_percent") is not None else selected.get("simulated_energy_saved_percent") or 0)
        bucket["uses"] += 1
        bucket["reward_total"] += reward
        bucket["energy_total"] += energy
        if str(outcome.get("comfort_status") or selected.get("simulated_comfort_status")).lower() in {"safe", "iaq improved", "comfort improved", "lighting dimmed safely"}:
            bucket["comfort_safe_count"] += 1
        if is_success(episode):
            bucket["successes"] += 1
        else:
            bucket["failures"] += 1

    stats = {}
    for strategy, bucket in buckets.items():
        uses = max(bucket["uses"], 1)
        success_rate = bucket["successes"] / uses
        comfort_safe_rate = bucket["comfort_safe_count"] / uses
        stats[strategy] = {
            "uses": bucket["uses"],
            "successes": bucket["successes"],
            "failures": bucket["failures"],
            "average_reward": round(bucket["reward_total"] / uses, 4),
            "average_energy_saved_percent": round(bucket["energy_total"] / uses, 4),
            "comfort_safe_rate": round(comfort_safe_rate, 4),
            "success_rate": round(success_rate, 4),
            "confidence": round(min(0.99, 0.45 + (success_rate * 0.45) + min(0.1, uses * 0.01)), 4),
        }
    return stats


def failure_key(action_type: str, situation_type: str, reason: str) -> str:
    return f"{action_type}|{situation_type}|{reason}"


def infer_failure_reason(plan: dict, outcome: dict) -> str:
    if plan.get("blocked") or plan.get("safety_status") == "blocked":
        return "safety_blocked"
    if plan.get("simulated_comfort_status") == "Unsafe" or outcome.get("comfort_status") == "Unsafe":
        return "comfort_violation"
    if float(plan.get("reward") or outcome.get("reward") or 0) < 0:
        return "negative_reward"
    return "failed_outcome"


def avoidance_rule(action_type: str, situation_type: str, reason: str) -> str:
    if action_type == "hvac_shutdown" or reason == "comfort_violation":
        return "Avoid aggressive HVAC shutdown when occupancy > 0."
    return f"Avoid {action_type} in {situation_type} when it previously caused {reason}."


def rebuild_failure_patterns(episodes: list[dict]) -> list[dict]:
    patterns: dict[str, dict] = {}
    for episode in episodes:
        situation = episode.get("situation") or {}
        situation_type = situation.get("event_type") or "unknown_situation"
        outcome = episode.get("execution_outcome") or {}
        candidates = episode.get("candidate_plans") or []
        for plan in candidates:
            reward = float(plan.get("reward") if plan.get("reward") is not None else 0)
            failed = plan.get("blocked") or plan.get("safety_status") == "blocked" or plan.get("simulated_comfort_status") == "Unsafe" or reward < 0
            if not failed:
                continue
            reason = infer_failure_reason(plan, outcome)
            for action_type in action_types_from_plan(plan) or ["unknown_action"]:
                key = failure_key(action_type, situation_type, reason)
                pattern = patterns.setdefault(
                    key,
                    {
                        "action_type": action_type,
                        "situation_type": situation_type,
                        "failure_reason": reason,
                        "count": 0,
                        "avoidance_rule": avoidance_rule(action_type, situation_type, reason),
                    },
                )
                pattern["count"] += 1
    return sorted(patterns.values(), key=lambda item: item["count"], reverse=True)


def save_experience_graph(data: dict) -> None:
    graph = normalize_graph(sanitize_value(data))
    graph["episodes"] = [episode for episode in graph.get("episodes", []) if isinstance(episode, dict)]
    graph["strategy_stats"] = rebuild_strategy_stats(graph["episodes"])
    graph["failure_patterns"] = rebuild_failure_patterns(graph["episodes"])
    graph["last_updated"] = utc_now_iso()
    EXPERIENCE_GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPERIENCE_GRAPH_PATH.write_text(json.dumps(graph, indent=2), encoding="utf-8")


def append_experience_episode(episode: dict) -> dict:
    graph = load_experience_graph()
    clean_episode = sanitize_value(dict(episode or {}))
    clean_episode.setdefault("created_at", utc_now_iso())
    clean_episode.setdefault("experience_id", f"exp_{utc_now_iso().replace(':', '').replace('-', '')}_{len(graph['episodes']) + 1:03d}")
    clean_episode.setdefault("source", "forgehive_layer8")
    graph["episodes"].append(clean_episode)
    save_experience_graph(graph)
    saved = load_experience_graph()
    return {"experience_graph_updated": True, "experience_id": clean_episode["experience_id"], "graph": saved}


def list_recent_experiences(limit: int = 10) -> list[dict]:
    episodes = load_experience_graph().get("episodes", [])
    return list(reversed(episodes))[:limit]


def summarize_experience_memory() -> dict:
    graph = load_experience_graph()
    recent_lessons = []
    for episode in reversed(graph.get("episodes", [])):
        for lesson in episode.get("lessons_learned", []) or []:
            if lesson not in recent_lessons:
                recent_lessons.append(lesson)
            if len(recent_lessons) >= 8:
                break
        if len(recent_lessons) >= 8:
            break
    return {
        "project": "ForgeHive",
        "experienceGraphEnabled": True,
        "totalExperiences": len(graph.get("episodes", [])),
        "topStrategies": get_top_strategies(),
        "failurePatterns": get_failure_patterns(),
        "recentLessons": recent_lessons,
        "lastUpdated": graph.get("last_updated"),
        "realBuildingExecution": False,
    }


def get_top_strategies(limit: int = 5) -> list[dict]:
    stats = load_experience_graph().get("strategy_stats", {})
    rows = []
    for strategy, item in stats.items():
        uses = int(item.get("uses", 0) or 0)
        success_rate = item.get("success_rate")
        if success_rate is None and uses:
            success_rate = float(item.get("successes", 0) or 0) / uses
        rows.append(
            {
                "strategy": strategy,
                "uses": uses,
                "successRate": round(float(success_rate or 0), 4),
                "averageReward": item.get("average_reward", 0),
                "averageEnergySavedPercent": item.get("average_energy_saved_percent", 0),
                "comfortSafeRate": item.get("comfort_safe_rate", 0),
                "confidence": item.get("confidence", 0),
            }
        )
    return sorted(rows, key=lambda row: (row["successRate"], row["averageReward"], row["uses"]), reverse=True)[:limit]


def get_failure_patterns(limit: int = 5) -> list[dict]:
    return load_experience_graph().get("failure_patterns", [])[:limit]

