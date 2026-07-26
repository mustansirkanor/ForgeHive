# ForgeHive Layer 8: Experience Graph / Episodic Memory

The original Knowledge Graph captures useful static relationships: an empty room suggests lighting, HVAC setpoint, and ventilation adjustments; high CO2 requires ventilation. That is necessary context, but it does not remember what actually happened when ForgeHive tried a plan.

Layer 8 adds episodic building memory. Each Experience Graph episode stores the situation, candidate plans, simulated EnergyPlus outcomes, ranking scores, Safety Governor decision, digital-twin execution result, reward, and compact lessons learned.

## Similar Situation Retrieval

ForgeHive extracts a `SituationSignature` from Layer 4, Layer 5, or demo API context. It compares the current signature with previous episodes using deterministic weighted similarity across event type, goal, occupancy, comfort, carbon state, anomaly count, CO2 range, and next meeting timing.

## LLM Planning Context

Before candidate generation, Layer 4 retrieves similar experiences and converts them into advisory prompt context. The prompt tells the LLM which historical plans worked, which action patterns failed, and that history is not authority. Current comfort, IAQ, carbon, simulation results, and the Safety Governor still override prior memory.

## RL Ranking Prior

Layer 5 ranking receives a small Experience Graph prior. Historically successful actions and preferred historical plan names get small bonuses. Known failure patterns, especially comfort violations, receive penalties. These priors bias ranking but do not dominate simulation reward or hard safety penalties.

## Safety Authority

The Safety Governor remains final authority. Experience memory never approves a risky action. Real building execution remains disabled; approved actions execute only inside the EnergyPlus digital twin.

## Stored Outcomes

After digital-twin execution and feedback learning, ForgeHive stores a compact episode in `data/experience/experience_graph.json`. Strategy statistics and failure patterns are recomputed from episodes so future similar situations can prefer successful plans and avoid known failures.

## Frontend Visualization

The Layer 7 dashboard now shows an Experience Graph panel with total experiences, similar past situations, best historical strategy, actions to prefer, actions to avoid, new episode storage, lessons learned, and a mini flow from Situation to Stored Memory.

