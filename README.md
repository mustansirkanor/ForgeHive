# ForgeHive

> **A safety-governed autonomous building optimization demo powered by Ollama, EnergyPlus, RL-style learning, Knowledge Graph memory, and a judge-facing web dashboard.**

ForgeHive is an autonomous building agent that understands building conditions, reasons about energy/comfort/carbon goals, simulates control decisions inside an **EnergyPlus digital twin**, checks every action through a **Safety Governor**, applies approved changes only to the simulated building model, measures the result, and learns from feedback.

**No real building equipment is controlled.**  
ForgeHive executes only inside the EnergyPlus digital twin.

---

## Final Status

| Item | Status |
|---|---|
| Final readiness score | **100 / 100** |
| Grade | **Excellent** |
| Automated tests | **30 passed, 0 failed** |
| Selected LLM provider | **Ollama** |
| Fallback used | **False** |
| EnergyPlus executed | **True** |
| Digital twin execution | **True** |
| Real building execution | **False** |
| Safety Governor used | **True** |
| RL/Bandit used | **True** |
| Knowledge Graph used | **True** |
| IDF lighting changes | **Applied** |
| IDF HVAC setpoint changes | **Applied** |
| IDF ventilation changes | **Applied** |

---

## What ForgeHive Does

Buildings often waste energy because HVAC, lighting, and ventilation systems continue operating even when spaces are empty or when carbon-aware scheduling could reduce impact. At the same time, aggressive energy-saving actions can damage occupant comfort and safety.

ForgeHive solves this by acting like an autonomous building operator:

```text
Building state changes
        ↓
ForgeHive understands the situation
        ↓
LLM generates candidate action bundles
        ↓
EnergyPlus simulates possible outcomes
        ↓
RL/Bandit + Knowledge Graph rank the best plan
        ↓
Safety Governor approves or rejects actions
        ↓
Approved actions are applied to the EnergyPlus IDF model
        ↓
Digital twin execution measures energy, carbon, and comfort
        ↓
Memory, bandit, and Knowledge Graph are updated
```

---

## Core Demo Idea

A user can ask:

```text
The meeting has ended and the room is empty and there is another meeting in the next 90 minutes, so we want the best plan for both situations.
```

ForgeHive should reason that it needs to:

```text
- Save energy while the room is empty.
- Dim unoccupied-zone lighting.
- Relax cooling setpoints safely.
- Reduce ventilation safely while the room is empty.
- Restore comfort, lighting, and fresh air before the next meeting.
- Avoid unsafe actions.
- Execute only in the EnergyPlus digital twin.
```

---

## Key Features

### 1. Natural Language Building Operator

Users can describe the building situation in normal language.

Example:

```text
The meeting room is empty now. Save energy but keep comfort safe.
```

ForgeHive converts this into a structured building-control goal.

---

### 2. Open-Source LLM Planning

ForgeHive uses a local/open-source LLM path through **Ollama**.

The LLM proposes candidate action bundles such as:

```text
- Dim lights in unoccupied zones.
- Relax cooling setpoint in unoccupied zones.
- Reduce ventilation safely.
- Restore comfort before occupancy returns.
```

The LLM does **not** directly execute actions.

---

### 3. MCP-Style Tool Layer

ForgeHive exposes controlled tools for:

```text
- Building intelligence
- Comfort checking
- Anomaly detection
- Candidate bundle validation
- Safety checking
- EnergyPlus simulation
- Reward ranking
- Final proof generation
```

This keeps the LLM inside a safe and auditable tool boundary.

---

### 4. EnergyPlus Digital Twin

ForgeHive uses **EnergyPlus** as the digital twin simulation engine.

It runs baseline and optimized simulations, then compares:

```text
- Electricity consumption
- Carbon impact
- Comfort status
- Anomaly count
- HVAC/lighting/ventilation changes
```

---

### 5. IDF Adapter

ForgeHive translates approved action bundles into actual EnergyPlus IDF model changes.

It can modify:

```text
- Lights objects
- Cooling setpoint schedules
- Outdoor air / ventilation objects
```

Example IDF changes:

```text
Lights SPACE1-1: 1584 → 396
Cooling Setpoint Schedule: 23.9°C → 28°C
Outdoor Air Flow: 0.00236 → 0.000944
```

---

### 6. Safety Governor

Before execution, every action passes through deterministic safety checks.

The Safety Governor checks:

```text
- HVAC comfort bounds
- Lighting safety
- Ventilation and IAQ safety
- Anomaly severity
- Expected impact
```

Unsafe example:

```text
Set occupied cooling setpoint to 30°C to save maximum energy.
```

Expected ForgeHive response:

```text
Rejected by Safety Governor because occupied cooling at 30°C violates comfort bounds.
```

---

### 7. RL/Bandit Ranking

ForgeHive uses an RL-style contextual bandit to rank strategies based on rewards.

Reward considers:

```text
- Energy saved
- Carbon reduced
- Comfort preserved
- Safety approval
- Anomaly risk
- Historical strategy performance
```

---

### 8. Knowledge Graph Memory

ForgeHive maintains a Knowledge Graph of building concepts and relationships.

Example relationships:

```text
Empty room → suggests lighting reduction
Empty room → suggests HVAC setback
High CO2 → requires ventilation improvement
High carbon window → suggests carbon-aware scheduling
Eco mode → optimizes energy savings
Comfort mode → protects occupant comfort
```

---

### 9. Closed-Loop Learning

After EnergyPlus execution, ForgeHive compares expected and actual outcomes.

It updates:

```text
- Strategy bandit confidence
- Building memory
- Knowledge Graph outcome history
```

---

### 10. Interactive Demo Website

The frontend dashboard allows judges to test ForgeHive visually.

It shows:

```text
- Building state before action
- Scenario simulator
- Natural language operator
- Candidate bundles
- Pipeline timeline
- Safety Governor decision
- EnergyPlus digital twin result
- IDF adapter proof
- Learning update
- Final judge proof
```

---

## Architecture

```text
User / Scenario
      ↓
Frontend Demo Dashboard
      ↓
Backend Demo API
      ↓
Layer 4 Cognitive Operator
      ↓
Ollama + MCP Tool Layer
      ↓
Candidate Action Bundles
      ↓
Layer 5 Closed Loop
      ↓
EnergyPlus Simulation
      ↓
RL/Bandit + Knowledge Graph Ranking
      ↓
Safety Governor
      ↓
IDF Adapter
      ↓
EnergyPlus Digital Twin Execution
      ↓
Feedback Learning + Proof Artifacts
```

---

## Source Structure

```text
backend/app/cognitive      LLM planning, provider routing, MCP tools, KG integration
backend/app/closed_loop    Simulation, ranking, safety gate, execution, learning
backend/app/energyplus     EnergyPlus runner, parser, strategy applier, IDF adapter
backend/app/intelligence   Building state, comfort, anomaly detection, scoring, memory
backend/app/decision       Safety Governor, domain agents, bandit, carbon scheduler
backend/app/final_audit    Final test matrix, artifact audit, readiness scoring
backend/app/demo_api       Local API used by the frontend demo

frontend/src               React judge-facing dashboard

data                       Memory, bandit, and Knowledge Graph stores
artifacts                  Proof exports and final submission package
runs                       EnergyPlus runtime outputs
docs                       Demo script, judge narrative, technical notes
```

---

## Important Submission Files

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

Judge-facing documents:

```text
docs/FINAL_DEMO_SCRIPT.md
docs/FINAL_JUDGE_NARRATIVE.md
docs/LAYER_7_FRONTEND_DEMO.md
```

---

## Running the Demo

### 1. Start Backend Demo API

From the repository root:

```bash
python -m backend.app.demo_api.server
```

On this machine, Python may also be run as:

```powershell
C:\Users\musta\AppData\Local\Programs\Python\Python313\python.exe -m backend.app.demo_api.server
```

The backend runs locally and exposes demo endpoints for the frontend.

---

### 2. Start Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

---

## Frontend Demo Modes

### Fast Demo Mode

Fast mode loads existing proof artifacts instantly.

Use this when presenting to judges because it is reliable and quick.

```text
Scenario → Latest proof artifacts → Dashboard visualization
```

---

### Live Ollama Demo Mode

Live mode runs the real backend loop:

```text
Scenario → Ollama → EnergyPlus → Safety Governor → IDF Adapter → Learning
```

This may take 30–90 seconds depending on system performance.

Use live mode once during the demo to prove the system is real.

---

## Suggested Demo Queries

### Empty Room Optimization

```text
The meeting room is empty now. Save energy but keep comfort safe.
```

Expected behavior:

```text
- Detect empty-room condition.
- Dim lighting.
- Relax cooling safely.
- Reduce ventilation safely.
- Simulate in EnergyPlus.
- Apply only inside the digital twin.
- Show energy and carbon reduction.
```

---

### Meeting Gap Optimization

```text
The meeting has ended and the room is empty and there is another meeting in the next 90 minutes, so we want the best plan for both situations.
```

Expected behavior:

```text
- Save energy during the empty period.
- Avoid comfort degradation before the next meeting.
- Restore lighting, HVAC, and ventilation before occupancy returns.
```

---

### High CO2 Scenario

```text
CO2 is too high in the meeting room. Fix air quality while keeping energy reasonable.
```

Expected behavior:

```text
- Prioritize indoor air quality.
- Increase or protect ventilation.
- Avoid unsafe energy-only optimization.
```

---

### Carbon-Aware Scenario

```text
Carbon intensity is high today. Reduce carbon impact without hurting comfort.
```

Expected behavior:

```text
- Prefer carbon-aware scheduling.
- Shift flexible load where possible.
- Maintain comfort boundaries.
```

---

### Unsafe Command Scenario

```text
Set occupied cooling setpoint to 30C to save maximum energy.
```

Expected behavior:

```text
- Safety Governor rejects the unsafe command.
- Comfort bounds are protected.
- Real building execution remains false.
```

---

## Backend API Endpoints

The frontend uses these local API endpoints:

```text
GET  /api/health
GET  /api/final-summary
GET  /api/scenarios
POST /api/scenarios/run
POST /api/operator/ask
GET  /api/artifacts
GET  /api/judge-summary
GET  /api/demo-script
```

Health response:

```json
{
  "status": "ok",
  "project": "ForgeHive",
  "realBuildingExecution": false
}
```

---

## Testing

### Final Backend Audit

```bash
python -m backend.app.final_audit.test_layer6_final_audit
```

Expected:

```text
Layer 6 final audit passed: ForgeHive is ready for final demo review.
```

---

### Demo API Test

```bash
python -m backend.app.demo_api.test_demo_api
```

---

### Frontend Build Test

```bash
cd frontend
npm run build
```

---

## Final Proof Summary

ForgeHive final proof demonstrates:

```text
- Real Ollama provider path
- EnergyPlus digital twin execution
- No real building execution
- Safety Governor approval/rejection
- RL/Bandit strategy ranking
- Knowledge Graph context
- Building memory update
- IDF lighting changes
- IDF HVAC setpoint changes
- IDF ventilation changes
- Judge-facing dashboard
- Final readiness score: 100/100
```

---

## Safety Boundary

ForgeHive is a digital twin demo.

It does not connect to:

```text
- Real HVAC equipment
- Real lighting controllers
- Real BMS hardware
- Real building actuators
```

All actions are applied only to copied EnergyPlus IDF files and simulated locally.

```text
Real building execution: false
Execution scope: EnergyPlus digital twin only
```

---

## Why ForgeHive Is Different

Most building dashboards only monitor data.

ForgeHive closes the loop:

```text
Monitor → Reason → Simulate → Rank → Safety-check → Execute in digital twin → Learn
```

It also does not blindly trust the LLM.

The LLM proposes actions, but deterministic systems decide whether those actions are safe, useful, and executable.

---

## Tech Stack

```text
Python
EnergyPlus
Ollama
OpenRouter fallback
MCP-style tool layer
React
Vite
Knowledge Graph JSON store
RL-style contextual bandit
FastAPI/local demo API
```

---

## Final Demo Statement

```text
ForgeHive does not blindly execute LLM actions. It simulates candidate plans in EnergyPlus, ranks them using reward learning and Knowledge Graph context, checks safety through a deterministic Safety Governor, executes only inside the digital twin, measures the result, and learns from feedback.
```