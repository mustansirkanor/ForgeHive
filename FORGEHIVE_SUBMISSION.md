# ForgeHive Submission Report

## Project Summary

ForgeHive is a closed-loop autonomous building optimization system built around an EnergyPlus digital twin. A natural-language operator request is converted into candidate control plans by a local Ollama LLM path, validated by schema and semantic guardrails, simulated in EnergyPlus, ranked with reward scoring plus learned bandit history and Knowledge Graph relevance, checked by a Safety Governor, executed only inside the digital twin, and then recorded back into memory, RL/bandit state, and the Knowledge Graph.

No real building equipment is controlled by this repository. All execution is limited to EnergyPlus IDF model edits and simulation runs.

## Deliverable Map

| Requirement | ForgeHive File / Folder |
| --- | --- |
| Fully functional source code | `backend/`, `frontend/`, `data/`, `runs/`, `artifacts/` |
| EnergyPlus API wrapper | `backend/app/energyplus/` |
| LLM agent orchestration | `backend/app/cognitive/` |
| Communication/demo API bus | `backend/app/demo_api/server.py` |
| Building baseline IDF | `ForgeHive_5ZoneAirCooled_Baseline.idf` |
| Modified runtime IDF | `ForgeHive_5ZoneAirCooled_Optimized_RuntimeEvaluation.idf` |
| Quantitative savings export | `artifacts/layer_5_closed_loop/layer5_7_dashboard_summary.json` |
| Final submission package | `artifacts/final_submission/forgehive_final_submission_package.json` |
| Final readiness audit | `artifacts/final_submission/forgehive_final_audit.json` |
| Demo script | `artifacts/final_submission/forgehive_demo_script.md` and `docs/FINAL_DEMO_SCRIPT.md` |
| Judge narrative | `artifacts/final_submission/forgehive_judge_summary.md` and `docs/FINAL_JUDGE_NARRATIVE.md` |

## Building Models

ForgeHive uses the EnergyPlus `5ZoneAirCooled.idf` example building as the baseline digital twin.

| Model | Purpose | Source |
| --- | --- | --- |
| `ForgeHive_5ZoneAirCooled_Baseline.idf` | Baseline building model before ForgeHive control | Copied from `C:\EnergyPlusV26-1-0\ExampleFiles\5ZoneAirCooled.idf` |
| `ForgeHive_5ZoneAirCooled_Optimized_RuntimeEvaluation.idf` | Modified model generated during the final runtime evaluation | Copied from latest clean Layer 5.7 execution |

Latest clean runtime execution:

```text
runs/layer_5/executions/20260726_111410_915661_energy_savings_bundle/modified_model.idf
```

## Quantitative Results

Final clean audit result:

```text
Readiness score: 100.0
Grade: Excellent
Automated tests: 30 passed, 0 failed
Artifact audit: passed
Demo audit: passed
Selected LLM provider: ollama
Fallback used: false
EnergyPlus executed: true
Digital twin execution: true
Real building execution: false
```

Final Layer 5.7 dashboard result:

```text
Candidate bundles generated: 3
Candidate bundles simulated: 3
Energy saved: 49.0322%
Carbon reduced: 49.0322%
Comfort status: Safe
Lighting IDF changes applied: true
HVAC setpoint IDF changes applied: true
Ventilation IDF changes applied: true
IDF adapter change count: 88
Safety Governor used: true
RL/bandit used: true
Knowledge Graph used: true
Memory updated: true
Bandit updated: true
Knowledge Graph updated: true
```

The primary proof files are:

```text
artifacts/layer_5_closed_loop/layer5_7_real_ollama_full_loop.json
artifacts/layer_5_closed_loop/layer5_7_dashboard_summary.json
artifacts/layer_5_closed_loop/layer5_7_idf_adapter_report.json
artifacts/final_submission/forgehive_final_audit.json
artifacts/final_submission/forgehive_readiness_score.json
```

## Architecture

The runtime flow is:

```text
Natural language request
  -> Intent and semantics extraction
  -> Building intelligence lookup
  -> Knowledge Graph context retrieval
  -> Ollama candidate plan generation
  -> Schema normalization and semantic guardrails
  -> Candidate diversity controller
  -> EnergyPlus simulation per candidate
  -> Reward ranking with RL/bandit prior and KG score
  -> Safety Governor approval
  -> IDF adapter model mutation
  -> EnergyPlus execution
  -> Memory, bandit, and KG learning update
  -> Dashboard/API response
```

Important modules:

```text
backend/app/cognitive/operator_intents.py
backend/app/cognitive/request_semantics.py
backend/app/cognitive/candidate_bundle_generator.py
backend/app/cognitive/llm_client.py
backend/app/cognitive/knowledge_graph.py
backend/app/closed_loop/reward_ranker.py
backend/app/closed_loop/bundle_simulator.py
backend/app/closed_loop/final_safety_gate.py
backend/app/closed_loop/digital_twin_executor.py
backend/app/energyplus/idf_adapter.py
backend/app/demo_api/server.py
frontend/src/App.jsx
```

## Prompt Engineering And Tool Calling

ForgeHive does not let the LLM directly control a building. The LLM generates structured candidate action bundles. The backend then treats those bundles as proposed tool calls and validates them before any simulation or IDF mutation.

The candidate prompt includes:

```text
- Current building context
- Knowledge Graph context
- Required action types inferred from the natural-language request
- Occupied/unoccupied target requirements
- Safety constraints
- JSON schema contract
- Instruction that Layer 4 cannot execute actions
```

Examples of supported action types:

```text
lighting_adjustment
hvac_setpoint_adjustment
ventilation_adjustment
preconditioning_schedule
carbon_schedule_shift
strategy_mode
no_direct_control_change
```

For a query such as:

```text
The meeting has ended and the room is empty and their meeting in next 90 mins so we want the best for both the situation
```

ForgeHive produces a timed plan:

```text
1. Save energy while the room is empty.
2. Dim unoccupied lighting.
3. Relax unoccupied cooling setpoint.
4. Reduce ventilation within safe empty-room bounds.
5. Restore comfort, lighting, and fresh air 20 minutes before the meeting in 90 minutes.
```

The `preconditioning_schedule` action is currently metadata-only for the IDF adapter. It is shown and safety-checked, while immediate lighting/HVAC/ventilation controls are applied to the EnergyPlus model.

## Prompt Latency Management

The LLM layer has provider timeouts and fallback handling:

```text
Default Ollama timeout: 90 seconds
Default OpenRouter timeout: 60 seconds
Default total LLM timeout: 140 seconds
```

The final audit was regenerated with OpenRouter disabled and local Ollama selected:

```text
selected_provider: ollama
fallback_used: false
```

If the LLM returns incomplete but understandable output, ForgeHive uses schema normalization and semantic repair to complete safe candidate plans before simulation. Unsafe or contradictory actions are rejected.

## Handling Lengthy Simulation Logs

EnergyPlus runs can produce large output files. ForgeHive handles this by:

```text
- Writing each simulation to a timestamped run directory.
- Parsing only the required EnergyPlus output metrics.
- Keeping full logs on disk under `runs/`.
- Exporting compact proof JSON under `artifacts/`.
- Showing concise dashboard fields in the frontend.
```

This keeps the UI responsive and prevents lengthy simulation logs from being pasted into the LLM prompt or frontend.

## How To Run

Backend API:

```powershell
C:\Users\musta\AppData\Local\Programs\Python\Python313\python.exe -m backend.app.demo_api.server
```

Frontend:

```powershell
cd frontend
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:5173
```

Recommended demo order:

```text
1. Run "Ready Demo".
2. Use "Example replay" for the timed 90-minute meeting query.
3. Use "Live autonomy" to prove the real Ollama + EnergyPlus path.
4. Open the AI options and decision graph to show RL, KG, Safety Governor, and IDF adapter behavior.
```

## Submission Status

ForgeHive is ready for GitHub repository submission.

```text
Final audit passed: true
Readiness score: 100.0
Grade: Excellent
Real building execution: false
```
