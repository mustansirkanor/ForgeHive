# ForgeHive Layer 1 Proof

Layer 1 proves that ForgeHive has a working EnergyPlus digital twin pipeline and can produce dashboard-ready metrics from a real baseline-vs-optimized simulation comparison.

## What Layer 1 Proves

- EnergyPlus is installed and callable.
- A manual baseline simulation completed successfully.
- The Python runner can launch EnergyPlus automatically.
- The parser extracts clean JSON metrics from EnergyPlus output files.
- The eco strategy creates an optimized IDF without changing the original model.
- The comparison layer shows measurable savings between baseline and optimized runs.
- The proof package exports JSON and Markdown artifacts for dashboard, documentation, demo video, and hackathon submission use.

## Confirmed Phase 1.5 Result

- Baseline electricity: 43,510.13 kWh
- Optimized electricity: 40,280.34 kWh
- Electricity savings: 3,229.79 kWh
- Savings percent: 7.42%
- Carbon savings: 1,453.40 kg
- Verdict: Optimization reduced energy consumption.

## Proof Package Outputs

Phase 1.6 generates these files under `artifacts/layer_1_proof/`:

- `layer1_proof.json`
- `dashboard_metrics.json`
- `layer1_summary.md`

## Phase 1.7 Comparison API Adapter

Phase 1.7 adds a framework-free comparison API module for future dashboard and demo use.

- `get_baseline_vs_forgehive_comparison()` returns rounded baseline, ForgeHive, impact, and metadata fields.
- `get_baseline_vs_aura_comparison()` returns the same response shape with the optimized system exposed as `aura`.
- Comfort violation minutes are fixed placeholder values in Layer 1.
- Layer 2 will replace the comfort placeholder with computed safety and comfort metrics.

## Next Layer 2 Direction

Layer 2 will add building state, strategy schema, safety governor and autonomous control brain.
