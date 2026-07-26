# Layer 5 Phase 5.1-5.3 Closed Loop

## What Layer 5 Adds

Layer 5 starts ForgeHive closed-loop autonomy. It receives Layer 4 candidate action bundles, simulates them in the EnergyPlus digital twin path, ranks the simulated plans with reward/RL-style scoring and Knowledge Graph relevance, and sends the selected plan through the existing Layer 3 Safety Governor.

Phase 5.1-5.3 does not execute controls. It produces an execution-ready plan only.

## Phase 5.1: EnergyPlus Action Bundle Simulation

Layer 5 converts each Layer 4 candidate bundle into a safe simulation strategy. Lighting, HVAC, ventilation, carbon-shift, strategy-mode, and no-direct-control actions are translated into simulation metadata and, where the existing IDF adapter supports it, EnergyPlus IDF changes.

Every simulation uses a unique directory under `runs/layer_5/`. The original baseline IDF is never modified in place. If EnergyPlus fails for one bundle, ForgeHive records a failed simulation result and continues with the remaining bundles.

## Phase 5.2: Reward Ranking With RL/Bandit And KG Context

Simulated bundles are ranked with:

- energy savings
- carbon reduction
- comfort status and comfort violation minutes
- anomaly penalties
- simulation success/failure
- safe action type pre-score
- read-only Layer 3 bandit prior
- Layer 4 Knowledge Graph relevance

The bandit is read only in Phase 5.2. Learning updates happen later after execution feedback.

## Phase 5.3: Final Safety Governor Approval

The selected bundle is converted into Layer 3 `ControlAction` objects. Each action is checked by the existing Safety Governor. High-risk or critical rejections block the final plan. If all actions are rejected, ForgeHive returns a safe no-action plan.

## What Is Still Not Executed

Phase 5.1-5.3 does not apply actions, does not control a real building, and does not mark learning feedback as if execution happened. `execution_applied` is always `false`.

## Why Execution Waits Until Phase 5.4

Phase 5.4 will apply approved actions inside the EnergyPlus digital twin and generate execution feedback. That feedback can then support memory, Knowledge Graph, and bandit learning in later phases.

## Example Flow

`The meeting room is empty now. Save energy but keep comfort safe.`

1. Layer 4 generates candidate bundles.
2. Phase 5.1 simulates each bundle in EnergyPlus.
3. Phase 5.2 ranks plans with reward, bandit prior, and KG relevance.
4. Phase 5.3 safety-checks the selected bundle.
5. ForgeHive returns an execution-ready plan with `execution_applied=false`.

## Demo Value

For Honeywell hackathon judges, Layer 5 proves ForgeHive is moving beyond recommendations: it can reason, simulate, rank, and safety-approve plans while preserving a clean boundary before execution.

## Test Commands

```powershell
python -m backend.app.closed_loop.test_bundle_simulator
python -m backend.app.closed_loop.test_reward_ranker
python -m backend.app.closed_loop.test_final_safety_gate
python -m backend.app.closed_loop.test_layer5_phase_1_3
```
