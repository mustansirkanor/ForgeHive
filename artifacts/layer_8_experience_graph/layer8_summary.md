# ForgeHive Layer 8 Experience Graph

ForgeHive does not relearn every building situation from scratch. It stores previous operational episodes, retrieves similar cases, and uses them as advisory memory for LLM planning and RL ranking.

The Experience Graph records the building situation, generated candidate bundles, EnergyPlus simulation outcomes, selected plan, Safety Governor approvals or blocks, digital-twin execution results, reward, and lessons learned.

History is advisory only. Every future decision is still simulated and safety-checked, and no real building execution is enabled.

