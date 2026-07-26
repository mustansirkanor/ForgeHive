from dataclasses import asdict, dataclass, is_dataclass


@dataclass
class BundleSimulationInput:
    bundle_id: str
    bundle_name: str
    goal: str
    event_type: str
    actions: list[dict]
    source_provider: str
    requires_simulation: bool
    created_by: str
    raw_bundle: dict


@dataclass
class BundleSimulationResult:
    bundle_id: str
    bundle_name: str
    simulation_status: str
    run_dir: str
    strategy_name: str
    actions_simulated: list[dict]
    energy_kwh: float
    carbon_kg: float
    comfort_violation_minutes: float
    comfort_status: str
    anomaly_count: int
    baseline_energy_kwh: float
    baseline_carbon_kg: float
    energy_saved_kwh: float
    energy_saved_percent: float
    carbon_reduced_kg: float
    carbon_reduced_percent: float
    simulation_notes: list[str]
    error: str | None
    raw_parser_output: dict
    idf_adapter_report: dict


@dataclass
class RankedBundle:
    rank: int
    bundle_id: str
    bundle_name: str
    total_score: float
    reward_score: float
    energy_score: float
    carbon_score: float
    comfort_score: float
    safety_score: float
    anomaly_score: float
    bandit_prior_score: float
    kg_relevance_score: float
    final_penalty: float
    penalty_reasons: list[str]
    simulation_result: dict
    ranking_reason: str


@dataclass
class FinalSafetyApproval:
    approved: bool
    selected_bundle_id: str | None
    selected_bundle_name: str | None
    risk_level: str
    safety_decisions: list[dict]
    blocked_actions: list[dict]
    approved_actions: list[dict]
    safety_summary: str
    execution_ready: bool
    execution_applied: bool
    execution_note: str


@dataclass
class DigitalTwinExecutionResult:
    phase: str
    execution_status: str
    execution_applied: bool
    execution_scope: str
    selected_bundle_id: str | None
    selected_bundle_name: str | None
    approved_actions_executed: list[dict]
    blocked_actions_not_executed: list[dict]
    run_dir: str
    strategy_name: str
    baseline_energy_kwh: float
    baseline_carbon_kg: float
    executed_energy_kwh: float
    executed_carbon_kg: float
    energy_saved_kwh: float
    energy_saved_percent: float
    carbon_reduced_kg: float
    carbon_reduced_percent: float
    comfort_violation_minutes: float
    comfort_status: str
    anomaly_count: int
    parser_output: dict
    idf_adapter_report: dict
    execution_notes: list[str]
    error: str | None


@dataclass
class FeedbackLearningReport:
    phase: str
    learning_status: str
    execution_success: bool
    expected_vs_actual: dict
    actual_reward: float
    bandit_updated: bool
    bandit_strategy: str
    memory_updated: bool
    knowledge_graph_updated: bool
    self_correction: dict
    learning_notes: list[str]
    error: str | None


@dataclass
class Layer5ClosedLoopPlan:
    project: dict
    phase: str
    user_message: str
    candidate_count: int
    simulation_count: int
    successful_simulation_count: int
    ranked_bundles: list[dict]
    selected_bundle: dict | None
    final_safety_approval: dict
    execution_ready: bool
    execution_applied: bool
    layer5_status: str
    dashboard_summary: dict
    proof: dict


def to_jsonable(obj):
    if is_dataclass(obj):
        return {key: to_jsonable(value) for key, value in asdict(obj).items()}
    if isinstance(obj, dict):
        return {key: to_jsonable(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [to_jsonable(value) for value in obj]
    if isinstance(obj, tuple):
        return [to_jsonable(value) for value in obj]
    return obj
