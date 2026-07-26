# ForgeHive Layer 3 Proof

## Layer 3 Overview
Layer 3 is the autonomous decision engine for ForgeHive. It converts Layer 2 building intelligence into safe, explainable action plans for closed-loop review.

Layer 3 does not execute actions. It only decides, ranks, safety-checks, and prepares approved actions for Layer 5 simulation, ranking, and final approval.

## What Was Implemented
- Standard `ControlAction` and `SafetyDecision` schemas
- Safety Governor for approve/reject decisions
- Energy, comfort, carbon, and anomaly decision agents
- Multi-agent supervisor
- Contextual bandit strategy selector
- Carbon-aware scheduling planner
- Decision API and dashboard-ready decision output

## Decision Flow
1. Read Layer 2 building intelligence.
2. Consult domain agents.
3. Use the contextual bandit to bias strategy selection.
4. Rank recommendations.
5. Safety-check the selected action.
6. Export a decision package for dashboard, future MCP tools, and Layer 5 closed-loop review.

## Multi-Agent Architecture
Agents consulted in the sample proof: energy_agent, comfort_agent, carbon_agent, anomaly_agent

Selected status: rejected

## Safety Governor Proof
- Safe action approved: True
- Unsafe action approved: False

## Carbon-Aware Scheduling
- Low-carbon windows found: 2
- High-carbon windows found: 1
- Expected carbon reduction: 6.0%

## RL / Contextual Bandit
Best average reward strategy: eco_mode

History count: 41

## Dashboard Output
- Autonomous decision ready: True
- Execution enabled: False
- Sample selected strategy: comfort_preserving_lighting
- Sample risk level: medium

## Future MCP Tools
- `get_autonomous_decision`: Ask ForgeHive to select and safety-check the best action for a goal.
- `get_dashboard_ready_decision`: Return compact decision output for dashboard or LLM explanation.
- `check_action_safety`: Approve or reject a proposed action before execution.
- `run_multi_agent_supervisor`: Consult energy, comfort, carbon, and anomaly agents.
- `build_carbon_aware_plan`: Generate carbon-aware operating schedule.

## What Layer 3 Does Not Do Yet
Layer 3 does not execute actions. It does not call MCP tools, LLMs, or EnergyPlus. It only prepares and safety-checks decisions.

## Ready for Layer 4
Layer 4 can expose these decision functions as MCP/LLM-callable tools while preserving the Safety Governor boundary.
