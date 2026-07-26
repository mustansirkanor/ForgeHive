# ForgeHive Layer 7 Frontend Demo

Layer 7 adds an interactive website and backend demo API that lets judges see ForgeHive as a product dashboard instead of raw logs.

The demo shows building state, natural-language intent, Ollama/provider trace, candidate bundles, EnergyPlus digital twin simulation, RL/Bandit and Knowledge Graph ranking, Safety Governor approval or rejection, IDF adapter changes, energy/carbon/comfort results, and learning updates.

## Backend Endpoints

- `GET /api/health`
- `GET /api/final-summary`
- `GET /api/scenarios`
- `POST /api/scenarios/run`
- `POST /api/operator/ask`
- `GET /api/artifacts`
- `GET /api/judge-summary`
- `GET /api/demo-script`

## Demo Modes

Fast artifact mode loads the Layer 5.7 and Layer 6 proof artifacts and returns instantly. Use this for the normal judge walk-through.

Live mode calls `run_real_ollama_full_loop_demo(message)`, which uses the real Layer 4 provider path and EnergyPlus digital twin. The UI displays that Ollama plus EnergyPlus may take 30-90 seconds.

## Start Commands

Backend:

```bash
python -m backend.app.demo_api.test_demo_api
python -m backend.app.demo_api.server
```

Frontend:

```bash
cd frontend
npm install
npm run build
npm run dev
```

The frontend defaults to `http://localhost:8000`. Override with `VITE_FORGEHIVE_API_BASE` if needed.

## Unsafe Scenario Flow

Choose `Unsafe command attempted`, then run Fast Demo.

Artifact mode returns a visible Safety Governor rejection:

```txt
Safety Governor rejected occupied cooling setpoint of 30C because it violates comfort bounds.
Safe alternative: keep occupied comfort bounds.
```

The response sets `safety.approved=false`, includes a blocked `hvac_setpoint_adjustment` with `cooling_setpoint_c=30`, and keeps `digitalTwin.realBuildingExecution=false`.

## Safety Note

ForgeHive Layer 7 is demo/frontend only. All execution scope is EnergyPlus digital twin only. The UI and API must never claim that ForgeHive controlled a real building, and no endpoint exposes `.env` values or API keys.

