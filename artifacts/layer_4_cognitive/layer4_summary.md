# ForgeHive Layer 4.6 Cognitive Operator

## What Phase 4.6 Adds
Phase 4.6 adds a natural language building operator that turns normal operator requests into detected intents, building context, knowledge graph matches, candidate action bundles, provider traces, and concise explanations.

## Example Prompts
- The meeting room is empty now. Save energy but keep comfort safe. -> empty_room_energy_saving (4 candidate bundles)
- CO2 is high in Zone 2. Improve air quality. -> iaq_improvement (2 candidate bundles)
- Grid carbon intensity is high today. Reduce emissions. -> carbon_reduction (4 candidate bundles)
- People are feeling too hot in the office. -> comfort_protection (2 candidate bundles)
- There is an abnormal HVAC energy spike. -> anomaly_response (3 candidate bundles)
- Why did ForgeHive choose this plan? -> explain_decision (4 candidate bundles)

## How ForgeHive Reasons
ForgeHive classifies the user request, reads Layer 2 building intelligence through MCP-style tools, retrieves Knowledge Graph context, generates candidate bundles through the configured LLM provider chain, validates candidate bundles, and explains the trace.

## Why Execution Is Blocked In Layer 4
Layer 4 is reasoning-only. It does not execute actions, apply controls, run EnergyPlus, or bypass the Safety Governor. Candidate bundles are proposals for later simulation and approval.

## What Layer 5 Does Next
Layer 5.1-5.3 will simulate candidate bundles in EnergyPlus, rank plans using reward/RL-style scoring, and apply final Safety Governor approval. Phase 5.4 will execute only approved digital-twin actions, and later feedback phases will record outcomes to memory, the Knowledge Graph, and the bandit selector.

## Dashboard Summary
- Status: complete
- Natural language operator enabled: True
- Real LLM provider enabled: False
- Execution enabled: False
- Ready for Layer 5: True

## Demo Value
For Honeywell hackathon judges, Phase 4.6 makes ForgeHive easy to demo: type a building request, inspect the reasoning trace, show the candidate plans, and prove that safety boundaries are enforced before Layer 5 closed-loop approval.
