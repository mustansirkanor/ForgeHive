# ForgeHive Final Judge Narrative

Buildings waste energy and carbon because operational decisions are often static, delayed, or detached from comfort and safety constraints. ForgeHive solves this with an autonomous closed-loop building agent.

ForgeHive uses an EnergyPlus digital twin to test decisions before applying them. A natural-language operator powered by a real open-source LLM path through Ollama generates candidate action bundles. An MCP-style tool layer exposes building intelligence, a Knowledge Graph supplies context, and reward/RL-style bandit scoring ranks candidate plans.

Before execution, the Safety Governor reviews the selected plan. ForgeHive then executes approved actions only inside the EnergyPlus digital twin, never a real building. The final demo measures energy, carbon, comfort, and anomaly outcomes, then updates memory, the Knowledge Graph, and the bandit learner.

The final Phase 5.7 demo demonstrates direct IDF adapter changes:
- Lighting applied in IDF: True
- HVAC setpoint applied in IDF: True
- Ventilation applied in IDF: True

Final readiness score: 100.0 (Excellent).

Honest safety boundary: no real building was controlled. ForgeHive is demo-ready as a digital-twin autonomous building optimization system.
