# ForgeHive Layer 5 Phase 5.4-5.6 Execution And Learning

## Overview
Layer 5.4-5.6 completes ForgeHive closed-loop autonomy inside the EnergyPlus digital twin. The loop executes only final Safety Governor-approved actions, measures actual digital-twin results, updates learning systems, and exports dashboard-ready proof.

No real building controls are touched.

## Phase 5.4: Digital Twin Execution
Phase 5.4 reads the Phase 5.1-5.3 plan and checks `final_safety_approval.execution_ready`.

If execution is not ready, ForgeHive returns a blocked execution result and does not start EnergyPlus.

If execution is ready, ForgeHive:
- uses only `approved_actions`;
- excludes all rejected actions;
- reconstructs an approved execution bundle;
- derives an EnergyPlus strategy from the bundle;
- writes a modified IDF copy to a unique run directory;
- runs EnergyPlus under `runs/layer_5/executions/`;
- parses EnergyPlus output;
- compares actual result against baseline metrics.

The original baseline IDF is never modified in place.

## Phase 5.5: Feedback Learning
Phase 5.5 compares the selected bundle's expected simulation result with actual digital-twin execution:
- expected versus actual energy savings;
- expected versus actual carbon reduction;
- expected versus actual comfort status;
- comfort regression detection;
- execution success detection.

The actual reward is based on:
- actual energy saved;
- actual carbon reduced;
- comfort status;
- anomaly count;
- execution failure penalty;
- comfort regression penalty.

## RL / Bandit Update
ForgeHive updates the Layer 3 strategy bandit only when:
- `execution_status == "executed"`;
- `execution_applied == true`.

Failed or blocked executions do not get recorded as successful learning.

## Memory Update
Successful digital-twin execution records a memory entry with:
- selected strategy;
- selected bundle name;
- approved actions;
- actual energy savings;
- actual carbon reduction;
- comfort result;
- prediction match status;
- execution run directory.

If memory cannot be updated, ForgeHive records a safe skipped note in the learning report.

## Knowledge Graph Update
Successful digital-twin execution updates the JSON-backed Knowledge Graph with:
- action bundle node;
- execution outcome node;
- `EXECUTED_IN_DIGITAL_TWIN` edge;
- action impact edges for energy, carbon, and comfort;
- strategy `LEARNED_OUTCOME` edge.

If KG update is unavailable, ForgeHive records a safe skipped note without breaking the loop.

## Self-Correction
ForgeHive generates transparent recommendations:
- underperforming energy savings reduce bundle confidence;
- comfort regression tightens comfort guardrails;
- carbon underperformance increases carbon-aware weighting;
- execution failure recommends safe no-action fallback and simulation mapping inspection;
- matched expectations increase confidence in the selected strategy.

## Phase 5.6: Dashboard And Proof Export
Phase 5.6 builds a final dashboard showing:
- LLM provider;
- MCP, KG, bandit, and Safety Governor usage;
- candidates generated and simulated;
- selected bundle and score;
- execution status and scope;
- measured energy, carbon, comfort, and anomaly impact;
- learning updates;
- self-correction summary.

## Artifacts
Generated under `artifacts/layer_5_closed_loop/`:
- `layer5_full_closed_loop_proof.json`
- `layer5_execution_result.json`
- `layer5_learning_report.json`
- `layer5_dashboard_final.json`
- `layer5_final_summary.md`

## Tests
Run:

```bash
python -m backend.app.closed_loop.test_digital_twin_executor
python -m backend.app.closed_loop.test_feedback_learner
python -m backend.app.closed_loop.test_layer5_phase_4_6
```

Previous Layer 5 checks:

```bash
python -m backend.app.closed_loop.test_bundle_simulator
python -m backend.app.closed_loop.test_reward_ranker
python -m backend.app.closed_loop.test_final_safety_gate
python -m backend.app.closed_loop.test_layer5_phase_1_3
```

## Demo Explanation
For Honeywell judges: ForgeHive turns a natural-language building request into candidate plans, validates them with LLM schema guardrails, simulates them in EnergyPlus, ranks them with reward/RL and Knowledge Graph context, runs the Safety Governor, executes only the approved plan inside the EnergyPlus digital twin, measures the result, and updates learning. Real building execution remains disabled.
