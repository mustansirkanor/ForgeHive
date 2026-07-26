import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime


@dataclass
class ZoneState:
    zone_id: str
    temperature_c: float
    humidity_percent: float
    occupancy_count: int
    co2_ppm: float
    lighting_level_percent: float
    comfort_status: str
    source: str


@dataclass
class EnergyState:
    electricity_kwh: float
    hvac_kwh: float
    lighting_kwh: float
    equipment_kwh: float
    source: str


@dataclass
class CarbonState:
    carbon_kg: float
    grid_intensity_kg_per_kwh: float
    source: str


@dataclass
class OccupancyState:
    total_occupancy: int
    occupied_zones: int
    occupancy_source: str


@dataclass
class ComfortState:
    comfort_score: float
    comfort_violation_minutes: int
    pmv_proxy: float
    status: str
    violations: list[str]
    source: str


@dataclass
class ActionHistoryEntry:
    timestamp: str
    strategy_name: str
    action_type: str
    description: str
    predicted_energy_saved_percent: float
    actual_energy_saved_percent: float | None
    safety_status: str


@dataclass
class BuildingState:
    building_id: str
    timestamp: str
    zones: list[ZoneState]
    energy: EnergyState
    carbon: CarbonState
    occupancy: OccupancyState
    comfort: ComfortState
    recent_actions: list[ActionHistoryEntry]


def to_dict(obj) -> dict:
    if not is_dataclass(obj):
        raise TypeError("to_dict expects a dataclass object.")
    return asdict(obj)


def to_json(obj) -> str:
    return json.dumps(to_dict(obj), indent=2)


def create_demo_building_state() -> BuildingState:
    timestamp = datetime(2026, 7, 25, 0, 0, 0).isoformat()
    demo_source = "demo_schema_value"

    zones = [
        ZoneState("SPACE1-1", 22.4, 45.0, 4, 650.0, 80.0, "Comfortable", demo_source),
        ZoneState("SPACE2-1", 23.1, 47.5, 3, 690.0, 75.0, "Comfortable", demo_source),
        ZoneState("SPACE3-1", 24.0, 49.0, 5, 720.0, 78.0, "Comfortable", demo_source),
        ZoneState("SPACE4-1", 22.8, 46.0, 2, 610.0, 70.0, "Comfortable", demo_source),
        ZoneState("SPACE5-1", 24.6, 50.0, 6, 760.0, 82.0, "Comfortable", demo_source),
    ]

    energy = EnergyState(
        electricity_kwh=40280.34,
        hvac_kwh=2466.30,
        lighting_kwh=20309.73,
        equipment_kwh=12586.74,
        source="layer_1_optimized_comparison",
    )

    carbon = CarbonState(
        carbon_kg=18126.15,
        grid_intensity_kg_per_kwh=0.45,
        source="layer_1_optimized_comparison",
    )

    occupancy = OccupancyState(
        total_occupancy=sum(zone.occupancy_count for zone in zones),
        occupied_zones=sum(1 for zone in zones if zone.occupancy_count > 0),
        occupancy_source=demo_source,
    )

    comfort = ComfortState(
        comfort_score=95.0,
        comfort_violation_minutes=0,
        pmv_proxy=0.1,
        status="Safe",
        violations=[],
        source="schema_placeholder_until_phase_2_3",
    )

    recent_actions = [
        ActionHistoryEntry(
            timestamp=timestamp,
            strategy_name="eco_mode",
            action_type="load_reduction",
            description="Reduced lighting and electric equipment loads using the Layer 1 eco strategy.",
            predicted_energy_saved_percent=7.42,
            actual_energy_saved_percent=7.42,
            safety_status="Safe",
        )
    ]

    return BuildingState(
        building_id="forgehive_demo_building",
        timestamp=timestamp,
        zones=zones,
        energy=energy,
        carbon=carbon,
        occupancy=occupancy,
        comfort=comfort,
        recent_actions=recent_actions,
    )


def validate_building_state(state: BuildingState) -> dict:
    errors = []

    if not state.building_id:
        errors.append("building_id must not be empty.")
    if not state.timestamp:
        errors.append("timestamp must not be empty.")
    if not state.zones:
        errors.append("zones list must not be empty.")

    for zone in state.zones:
        if not zone.zone_id:
            errors.append("zone_id must not be empty.")
        if not -20 <= zone.temperature_c <= 60:
            errors.append(f"{zone.zone_id} temperature_c must be between -20 and 60.")
        if not 0 <= zone.humidity_percent <= 100:
            errors.append(f"{zone.zone_id} humidity_percent must be between 0 and 100.")
        if zone.occupancy_count < 0:
            errors.append(f"{zone.zone_id} occupancy_count must be >= 0.")
        if zone.co2_ppm <= 0:
            errors.append(f"{zone.zone_id} co2_ppm must be > 0.")
        if not 0 <= zone.lighting_level_percent <= 100:
            errors.append(f"{zone.zone_id} lighting_level_percent must be between 0 and 100.")

    if state.energy.electricity_kwh < 0:
        errors.append("electricity_kwh must be >= 0.")
    if state.carbon.carbon_kg < 0:
        errors.append("carbon_kg must be >= 0.")
    if not 0 <= state.comfort.comfort_score <= 100:
        errors.append("comfort_score must be between 0 and 100.")
    if state.comfort.comfort_violation_minutes < 0:
        errors.append("comfort_violation_minutes must be >= 0.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
