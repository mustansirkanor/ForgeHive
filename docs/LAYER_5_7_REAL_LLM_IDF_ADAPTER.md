# ForgeHive Layer 5 Phase 5.7 Real LLM And IDF Adapter

## What Phase 5.7 Adds
Phase 5.7 connects the full ForgeHive loop to the real Layer 4 provider path and hardens EnergyPlus IDF modification proof.

The final demo flow is:
1. Natural language request.
2. Layer 4 natural language operator.
3. Ollama, OpenRouter, or mock fallback candidate generation.
4. Layer 5 EnergyPlus simulation.
5. Reward/RL and Knowledge Graph ranking.
6. Safety Governor approval.
7. EnergyPlus digital twin execution only.
8. Feedback learning into bandit, memory, and KG.
9. Dashboard/proof artifact export.

No real building is controlled.

## What An IDF Adapter Is
The IDF adapter safely edits a copied EnergyPlus IDF file from approved ForgeHive action bundles. It treats IDF objects as semicolon-terminated text blocks, preserves the source IDF, writes only to a target IDF inside a run directory, and logs before/after values for every actual change.

Implementation:
- `backend/app/energyplus/idf_adapter.py`
- main function: `apply_action_bundle_to_idf(...)`

## Lighting Application
For `lighting_adjustment`, the adapter supports:
- `lighting_level_percent`
- `brightness`
- `value`
- `reduction_percent`

It finds `Lights` objects and changes safe design-level numeric fields. Lighting level is clamped to 10-100%. Occupied-zone lighting is not reduced below 50%.

## HVAC Setpoint Application
For `hvac_setpoint_adjustment`, the adapter supports:
- `cooling_setpoint_c`
- `heating_setpoint_c`
- `setpoint_c`
- `value`
- `applies_to_occupied_zones`

Cooling is clamped to 21-26C for occupied zones and 21-30C for unoccupied zones. Heating is clamped to 16-24C.

The adapter attempts conservative edits to:
- `Schedule:Compact`
- `Schedule:Constant`
- `Schedule:Ruleset`
- `ThermostatSetpoint:DualSetpoint`
- `ZoneControl:Thermostat`

If no safe object is found, the action is recorded as metadata-only with a warning.

## Ventilation Application
For `ventilation_adjustment`, the adapter supports:
- `ventilation_percent`
- `outdoor_air_percent`
- `value`
- `applies_to_occupied_zones`

Ventilation is clamped to 30-100%. Occupied-zone ventilation is not reduced below 50% unless explicitly unoccupied. Outdoor air is never set to zero.

The adapter attempts conservative edits to:
- `DesignSpecification:OutdoorAir`
- `ZoneVentilation:DesignFlowRate`
- `Controller:OutdoorAir`
- `AirLoopHVAC:OutdoorAirSystem`
- ventilation or outdoor-air schedules

If no safe object is found, the action is recorded as metadata-only with a warning.

## Why Some Actions Are Metadata-Only
Some EnergyPlus models do not expose editable HVAC or ventilation objects in an obvious safe format. ForgeHive does not guess. It logs metadata-only actions and warnings instead of claiming a change that did not happen.

## Real Ollama Full-Loop Demo
`backend/app/closed_loop/real_llm_full_loop.py` runs the real provider path:
- sets `FORGEHIVE_LLM_MODE=auto`;
- sets provider priority to `ollama,openrouter,mock`;
- calls the Layer 4 operator;
- records provider trace and schema repair metadata;
- passes real candidate bundles into the full Layer 5 loop;
- exports Phase 5.7 proof artifacts.

Ollama is preferred. OpenRouter is accepted when Ollama is unavailable. Mock is transparent and not judge-ready for strict real-provider proof.

## Strict Demo
Run:

```bash
python -m backend.app.closed_loop.test_phase57_real_llm_full_loop
```

To require a real provider:

```bash
FORGEHIVE_REQUIRE_REAL_LLM_DEMO=true python -m backend.app.closed_loop.test_phase57_real_llm_full_loop
```

## Dashboard Proof
The dashboard shows:
- selected provider;
- whether Ollama/OpenRouter/mock was used;
- EnergyPlus and digital twin execution status;
- real building execution false;
- lighting/HVAC/ventilation IDF application flags;
- metadata-only actions;
- candidate and simulation counts;
- Safety Governor, RL/bandit, KG, and memory status;
- measured energy, carbon, and comfort result;
- judge-ready status.

## Artifacts
Generated under `artifacts/layer_5_closed_loop/`:
- `layer5_7_real_ollama_full_loop.json`
- `layer5_7_idf_adapter_report.json`
- `layer5_7_dashboard_summary.json`
- `layer5_7_summary.md`

## Tests
Run:

```bash
python -m backend.app.energyplus.test_idf_adapter
python -m backend.app.closed_loop.test_phase57_real_llm_full_loop
python -m backend.app.closed_loop.test_phase57_artifacts
```

Previous Layer 5 checks:

```bash
python -m backend.app.closed_loop.test_digital_twin_executor
python -m backend.app.closed_loop.test_feedback_learner
python -m backend.app.closed_loop.test_layer5_phase_4_6
python -m backend.app.closed_loop.test_bundle_simulator
python -m backend.app.closed_loop.test_reward_ranker
python -m backend.app.closed_loop.test_final_safety_gate
python -m backend.app.closed_loop.test_layer5_phase_1_3
```

## Safety Reminder
Phase 5.7 executes only inside the EnergyPlus digital twin. It does not control a real building, does not bypass the Safety Governor, does not execute rejected actions, and does not modify the original baseline IDF in place.
