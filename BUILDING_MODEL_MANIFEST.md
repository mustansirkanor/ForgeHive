# ForgeHive Building Model Manifest

## Root Model Files

| File | Role | Size | SHA256 |
| --- | --- | ---: | --- |
| `ForgeHive_5ZoneAirCooled_Baseline.idf` | Baseline EnergyPlus building model | 169,736 bytes | `0187CF7F2CA9C27C43D435A68A8C66A557A43678846813A7E21463A0B0C716CD` |
| `ForgeHive_5ZoneAirCooled_Optimized_RuntimeEvaluation.idf` | Modified model from final clean runtime evaluation | 169,724 bytes | `6A43862E4445601286DB702DA15072FD0870B282CA227C3E260746DEE1606840` |

## Baseline Source

```text
C:\EnergyPlusV26-1-0\ExampleFiles\5ZoneAirCooled.idf
```

## Optimized Runtime Source

```text
runs/layer_5/executions/20260726_111410_915661_energy_savings_bundle/modified_model.idf
```

## Final Runtime Proof

```text
artifacts/layer_5_closed_loop/layer5_7_real_ollama_full_loop.json
artifacts/layer_5_closed_loop/layer5_7_idf_adapter_report.json
artifacts/layer_5_closed_loop/layer5_7_dashboard_summary.json
```

## Final Clean Result

```text
Selected provider: ollama
Fallback used: false
Candidate bundles generated: 3
Candidate bundles simulated: 3
Energy saved: 49.0322%
Carbon reduced: 49.0322%
Comfort status: Safe
IDF adapter changes: 88
Real building execution: false
```

The optimized IDF is the digital-twin runtime model produced after ForgeHive selected and approved the final `energy_savings_bundle`.
