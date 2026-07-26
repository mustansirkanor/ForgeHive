# ForgeHive

ForgeHive is an autonomous building optimization demo that uses a local LLM planner, an EnergyPlus digital twin, RL-style bandit ranking, a Knowledge Graph, and a Safety Governor to test and apply building-control actions safely.

The final demo executes only inside the EnergyPlus digital twin. No real building equipment is controlled.

## Submission Files

Start here:

```text
FORGEHIVE_SUBMISSION.md
BUILDING_MODEL_MANIFEST.md
ForgeHive_5ZoneAirCooled_Baseline.idf
ForgeHive_5ZoneAirCooled_Optimized_RuntimeEvaluation.idf
```

Key proof artifacts:

```text
artifacts/final_submission/forgehive_final_audit.json
artifacts/final_submission/forgehive_readiness_score.json
artifacts/final_submission/forgehive_final_submission_package.json
artifacts/layer_5_closed_loop/layer5_7_real_ollama_full_loop.json
artifacts/layer_5_closed_loop/layer5_7_dashboard_summary.json
artifacts/layer_5_closed_loop/layer5_7_idf_adapter_report.json
```

## Final Status

```text
Readiness score: 100.0
Grade: Excellent
Automated tests: 30 passed, 0 failed
Selected provider: ollama
Fallback used: false
EnergyPlus executed: true
Digital twin execution: true
Real building execution: false
Safety Governor used: true
RL/bandit used: true
Knowledge Graph used: true
```

## Run The Demo

Backend:

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

## Suggested Demo Query

```text
The meeting has ended and the room is empty and their meeting in next 90 mins so we want the best for both the situation
```

Expected behavior:

```text
- Save energy while the room is empty.
- Dim unoccupied lights.
- Relax unoccupied cooling.
- Reduce empty-room ventilation safely.
- Restore comfort, lighting, and fresh air before the next meeting.
```

## Source Structure

```text
backend/app/cognitive      LLM planning, intent semantics, KG integration
backend/app/closed_loop    simulation, reward ranking, safety, execution, learning
backend/app/energyplus     EnergyPlus runner, parser, IDF adapter
backend/app/demo_api       local API for the frontend demo
frontend/src               React judge-facing dashboard
data                       memory, bandit, and Knowledge Graph stores
artifacts                  proof exports and final submission package
runs                       EnergyPlus runtime outputs
docs                       judge script and narrative
```
