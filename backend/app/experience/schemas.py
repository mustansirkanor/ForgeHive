from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class SituationSignature:
    event_type: str
    goal: str
    occupancy: int | None = None
    temperature_c: float | None = None
    co2_ppm: float | None = None
    carbon_state: str | None = None
    next_meeting_minutes: int | None = None
    comfort_status: str | None = None
    anomaly_count: int | None = None
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass
class CandidatePlanExperience:
    bundle_id: str
    bundle_name: str
    action_types: list[str] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    simulated_energy_saved_percent: float | None = None
    simulated_carbon_reduced_percent: float | None = None
    simulated_comfort_status: str | None = None
    simulation_success: bool = False
    rank: int | None = None
    score: float | None = None
    reward: float | None = None
    safety_status: str | None = None
    blocked: bool = False


@dataclass
class ExecutionOutcomeExperience:
    execution_status: str
    energy_saved_percent: float | None = None
    carbon_reduced_percent: float | None = None
    comfort_status: str | None = None
    anomaly_count: int | None = None
    reward: float | None = None
    bandit_updated: bool = False
    memory_updated: bool = False
    knowledge_graph_updated: bool = False
    real_building_execution: bool = False
    digital_twin_execution: bool = True


@dataclass
class ExperienceEpisode:
    experience_id: str
    created_at: str
    situation: SituationSignature | dict
    candidate_plans: list[CandidatePlanExperience | dict] = field(default_factory=list)
    selected_plan: CandidatePlanExperience | dict | None = None
    approved_actions: list[dict] = field(default_factory=list)
    blocked_actions: list[dict] = field(default_factory=list)
    execution_outcome: ExecutionOutcomeExperience | dict | None = None
    lessons_learned: list[str] = field(default_factory=list)
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)
    source: str = "forgehive_layer8"


def to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    return value


def situation_signature(**kwargs) -> dict:
    return to_dict(SituationSignature(**kwargs))


def candidate_plan_experience(**kwargs) -> dict:
    return to_dict(CandidatePlanExperience(**kwargs))


def execution_outcome_experience(**kwargs) -> dict:
    return to_dict(ExecutionOutcomeExperience(**kwargs))


def experience_episode(**kwargs) -> dict:
    return to_dict(ExperienceEpisode(**kwargs))

