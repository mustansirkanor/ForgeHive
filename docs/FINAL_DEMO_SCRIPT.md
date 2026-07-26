# ForgeHive Final Demo Script

## 1. Natural Language Prompt
`The meeting room is empty now. Save energy but keep comfort safe.`

## 2. Layer 4 Intent And Provider Trace
Show that the Layer 4 operator selected provider `ollama` with fallback_used=False.

## 3. Candidate Bundles
Show 3 generated candidate bundle(s), including lighting, HVAC, and ventilation proposals.

## 4. EnergyPlus Simulation
Show Layer 5 simulation results for candidate bundles in the EnergyPlus digital twin.

## 5. Reward Ranking With RL/KG
Show reward score, bandit/RL prior, Knowledge Graph relevance, and selected bundle.

## 6. Safety Governor Approval
Show final Safety Governor approval and rejected-action handling before execution.

## 7. IDF Adapter Changes
Lighting applied: True
HVAC setpoint applied: True
Ventilation applied: True
Adapter change count: 88

## 8. Digital Twin Execution Result
Digital twin execution: True
Real building execution: False
Energy saved: 49.0322%
Carbon reduced: 49.0322%
Comfort status: Safe

## 9. Learning Update
Bandit updated: True
Memory updated: True
Knowledge Graph updated: True

## 10. Final Dashboard
judgeReady: True
End by emphasizing that ForgeHive executed only inside the EnergyPlus digital twin.
