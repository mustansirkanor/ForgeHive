import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_kg_file_path() -> Path:
    return PROJECT_ROOT / "data" / "knowledge_graph" / "forgehive_kg.json"


def initial_nodes() -> dict:
    entries = [
        ("zone:whole_building", "zone", "Whole Building"),
        ("zone:unoccupied_zones", "zone", "Unoccupied Zones"),
        ("zone:occupied_zones", "zone", "Occupied Zones"),
        ("equipment:hvac", "equipment", "HVAC"),
        ("equipment:lighting", "equipment", "Lighting"),
        ("equipment:ventilation", "equipment", "Ventilation"),
        ("equipment:plug_loads", "equipment", "Plug Loads"),
        ("condition:empty_room", "condition", "Empty Room"),
        ("condition:high_occupancy", "condition", "High Occupancy"),
        ("condition:high_co2", "condition", "High CO2"),
        ("condition:lighting_waste", "condition", "Lighting Waste"),
        ("condition:hvac_abnormal_load", "condition", "HVAC Abnormal Load"),
        ("condition:high_carbon_window", "condition", "High Carbon Window"),
        ("action:lighting_adjustment", "action", "Lighting Adjustment"),
        ("action:hvac_setpoint_adjustment", "action", "HVAC Setpoint Adjustment"),
        ("action:ventilation_adjustment", "action", "Ventilation Adjustment"),
        ("action:carbon_schedule_shift", "action", "Carbon Schedule Shift"),
        ("action:equipment_adjustment", "action", "Equipment Adjustment"),
        ("strategy:eco_mode", "strategy", "Eco Mode"),
        ("strategy:comfort_mode", "strategy", "Comfort Mode"),
        ("strategy:carbon_aware_mode", "strategy", "Carbon Aware Mode"),
        ("strategy:balanced_mode", "strategy", "Balanced Mode"),
        ("outcome:energy_saved", "outcome", "Energy Saved"),
        ("outcome:carbon_reduced", "outcome", "Carbon Reduced"),
        ("outcome:comfort_safe", "outcome", "Comfort Safe"),
        ("outcome:iaq_safe", "outcome", "IAQ Safe"),
        ("outcome:anomaly_resolved", "outcome", "Anomaly Resolved"),
    ]
    return {node_id: {"id": node_id, "type": node_type, "label": label, "properties": {}} for node_id, node_type, label in entries}


def initial_edges() -> list[dict]:
    return [
        {"source": "condition:empty_room", "relation": "SUGGESTS", "target": "action:lighting_adjustment", "properties": {}},
        {"source": "condition:empty_room", "relation": "SUGGESTS", "target": "action:hvac_setpoint_adjustment", "properties": {}},
        {"source": "condition:empty_room", "relation": "SUGGESTS", "target": "action:ventilation_adjustment", "properties": {}},
        {"source": "action:lighting_adjustment", "relation": "REDUCES", "target": "outcome:energy_saved", "properties": {}},
        {"source": "action:hvac_setpoint_adjustment", "relation": "AFFECTS", "target": "outcome:comfort_safe", "properties": {}},
        {"source": "action:ventilation_adjustment", "relation": "AFFECTS", "target": "outcome:iaq_safe", "properties": {}},
        {"source": "condition:high_co2", "relation": "REQUIRES", "target": "action:ventilation_adjustment", "properties": {}},
        {"source": "condition:high_carbon_window", "relation": "SUGGESTS", "target": "action:carbon_schedule_shift", "properties": {}},
        {"source": "strategy:eco_mode", "relation": "OPTIMIZES", "target": "outcome:energy_saved", "properties": {}},
        {"source": "strategy:carbon_aware_mode", "relation": "OPTIMIZES", "target": "outcome:carbon_reduced", "properties": {}},
        {"source": "strategy:comfort_mode", "relation": "PROTECTS", "target": "outcome:comfort_safe", "properties": {}},
    ]


def ensure_knowledge_graph() -> Path:
    path = get_kg_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        graph = {"nodes": initial_nodes(), "edges": initial_edges(), "events": [], "metadata": {"created_by": "layer_4_4"}}
        path.write_text(json.dumps(graph, indent=2))
    return path


def load_knowledge_graph() -> dict:
    path = ensure_knowledge_graph()
    try:
        with path.open(errors="ignore") as file:
            graph = json.load(file)
    except json.JSONDecodeError:
        graph = {"nodes": initial_nodes(), "edges": initial_edges(), "events": [], "metadata": {"recovered": True}}
        save_knowledge_graph(graph)
    graph.setdefault("nodes", {})
    graph.setdefault("edges", [])
    graph.setdefault("events", [])
    graph.setdefault("metadata", {})
    return graph


def save_knowledge_graph(graph: dict) -> None:
    ensure_knowledge_graph()
    get_kg_file_path().write_text(json.dumps(graph, indent=2))


def add_node(node_id: str, node_type: str, label: str, properties: dict | None = None) -> dict:
    graph = load_knowledge_graph()
    graph["nodes"][node_id] = {"id": node_id, "type": node_type, "label": label, "properties": properties or {}}
    save_knowledge_graph(graph)
    return graph["nodes"][node_id]


def add_edge(source: str, relation: str, target: str, properties: dict | None = None) -> dict:
    graph = load_knowledge_graph()
    edge = {"source": source, "relation": relation, "target": target, "properties": properties or {}}
    if not any(existing["source"] == source and existing["relation"] == relation and existing["target"] == target for existing in graph["edges"]):
        graph["edges"].append(edge)
        save_knowledge_graph(graph)
    return edge


def record_event(event_type: str, details: dict) -> dict:
    graph = load_knowledge_graph()
    event = {"timestamp": datetime.now(timezone.utc).isoformat(), "event_type": event_type, "details": details}
    graph["events"].append(event)
    save_knowledge_graph(graph)
    return event


def find_nodes_by_type(node_type: str) -> list[dict]:
    return [node for node in load_knowledge_graph()["nodes"].values() if node.get("type") == node_type]


def find_edges_for_node(node_id: str) -> list[dict]:
    return [edge for edge in load_knowledge_graph()["edges"] if edge["source"] == node_id or edge["target"] == node_id]


def query_relationships(keyword: str) -> dict:
    graph = load_knowledge_graph()
    keyword = keyword.lower()
    nodes = [node for node in graph["nodes"].values() if keyword in json.dumps(node).lower()]
    edges = [edge for edge in graph["edges"] if keyword in json.dumps(edge).lower()]
    return {"nodes": nodes, "edges": edges}


def infer_conditions_from_building_context(building_context: dict) -> list[str]:
    conditions = []
    occupancy = building_context.get("building_state", {}).get("occupancy", {})
    anomalies = building_context.get("anomalies", {}).get("anomalies", [])
    anomaly_types = {anomaly.get("type") for anomaly in anomalies}
    goal = building_context.get("goal", "")
    event_type = building_context.get("event_type", "")

    if occupancy.get("total_occupancy") == 0 or "empty_room" in event_type:
        conditions.append("condition:empty_room")
    if anomaly_types.intersection({"poor_iaq", "elevated_co2"}) or "iaq" in goal or "co2" in event_type:
        conditions.append("condition:high_co2")
    if "lighting_waste" in anomaly_types:
        conditions.append("condition:lighting_waste")
    if "hvac_abnormal_load" in anomaly_types:
        conditions.append("condition:hvac_abnormal_load")
    if "carbon" in goal or "high_carbon" in event_type:
        conditions.append("condition:high_carbon_window")

    return conditions


def get_relevant_knowledge_context(goal: str, event_type: str, building_context: dict) -> dict:
    graph = load_knowledge_graph()
    context = dict(building_context or {})
    context["goal"] = goal
    context["event_type"] = event_type
    matched_conditions = infer_conditions_from_building_context(context)
    relationships = []
    relevant_actions = set()
    relevant_strategies = set()

    for condition in matched_conditions:
        for edge in graph["edges"]:
            if edge["source"] == condition:
                relationships.append(edge)
                if edge["target"].startswith("action:"):
                    relevant_actions.add(edge["target"].split(":", 1)[1])

    if "energy" in goal:
        relevant_strategies.add("eco_mode")
    if "carbon" in goal:
        relevant_strategies.add("carbon_aware_mode")
        relevant_actions.add("carbon_schedule_shift")
    if "comfort" in goal:
        relevant_strategies.add("comfort_mode")
        relevant_actions.add("hvac_setpoint_adjustment")
    if "iaq" in goal:
        relevant_strategies.add("iaq_priority_mode")
        relevant_actions.add("ventilation_adjustment")
    if "lighting" in goal:
        relevant_actions.add("lighting_adjustment")

    summary = f"Matched {len(matched_conditions)} conditions and {len(relevant_actions)} relevant actions for goal '{goal}'."
    return {
        "matched_conditions": matched_conditions,
        "relevant_actions": sorted(relevant_actions),
        "relevant_strategies": sorted(relevant_strategies),
        "relationships": relationships,
        "summary": summary,
    }


def record_candidate_bundle_to_kg(bundle: dict, validation_result: dict | None = None) -> dict:
    return record_event(
        "candidate_bundle_generated",
        {
            "bundle_name": bundle.get("bundle_name", ""),
            "goal": bundle.get("goal", ""),
            "event_type": bundle.get("event_type", ""),
            "action_types": [action.get("action_type") for action in bundle.get("actions", [])],
            "valid": validation_result.get("valid") if validation_result else None,
        },
    )


def record_operator_trace_to_kg(trace: dict) -> dict:
    return record_event("cognitive_operator_trace", trace)
