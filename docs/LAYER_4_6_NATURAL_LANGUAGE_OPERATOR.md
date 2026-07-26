# Layer 4.6 Natural Language Building Operator

## Purpose

Phase 4.6 adds a natural language operator for ForgeHive. A user can type a normal building request, and Layer 4 returns a cognitive trace with detected intent, building intelligence, Knowledge Graph context, candidate bundles, LLM provider trace, safety guardrails, and a Layer 5 handoff.

Layer 4 remains reasoning-only. It does not execute actions, run EnergyPlus, or apply building controls.

## Supported Intents

- `empty_room_energy_saving`
- `carbon_reduction`
- `comfort_protection`
- `iaq_improvement`
- `anomaly_response`
- `explain_decision`
- `safety_review`
- `general_building_status`

## Example Prompts

- The meeting room is empty now. Save energy but keep comfort safe.
- CO2 is high in Zone 2. Improve air quality.
- Grid carbon intensity is high today. Reduce emissions.
- People are feeling too hot in the office.
- There is an abnormal HVAC energy spike.
- Why did ForgeHive choose this plan?

## Example Output Shape

```json
{
  "project": {"name": "ForgeHive", "layer": "Layer 4", "phase": "Phase 4.6"},
  "user_message": "...",
  "intent": {"intent": "...", "goal": "...", "event_type": "..."},
  "building_summary": {},
  "knowledge_context": {},
  "candidate_bundles": [],
  "candidate_count": 0,
  "primary_candidate": null,
  "llm_provider_trace": {},
  "safety_guardrails": [],
  "execution_enabled": false,
  "execution_allowed": false,
  "reasoning_only": true,
  "ready_for_layer5": true,
  "layer5_handoff": {},
  "explanation": "..."
}
```

## Cognitive Trace

The operator explains what the user asked, how the intent was routed, what the current building score/comfort/anomaly state looks like, what the Knowledge Graph contributed, how many candidate bundles were generated, and why execution did not happen in Layer 4.

## LLM Provider Trace

The response preserves provider metadata from Phase 4.5:

- selected provider
- attempted providers
- fallback status
- error summary
- model
- latency
- schema repair notes
- timeout and retry metadata

## MCP + KG + Candidate Bundle Flow

1. Classify the natural language request.
2. Read Layer 2 building intelligence through MCP-style tools.
3. Retrieve Knowledge Graph context for the detected goal/event.
4. Generate candidate bundles using Ollama, OpenRouter, or mock fallback.
5. Validate candidate bundles against the Layer 4 schema.
6. Return a clear explanation and Layer 5 handoff.

## Safety

Layer 4 cannot execute actions. Candidate bundles are proposals only. The Safety Governor remains required before any future execution. EnergyPlus simulation and approved action execution are reserved for Layer 5.

## Layer 5 Handoff

Layer 5 will simulate candidate bundles in EnergyPlus, rank them with reward/RL-style scoring, apply Safety Governor approval, execute only approved actions in the digital twin, and record feedback to memory, the Knowledge Graph, and the bandit selector.

## Demo Value

For Honeywell hackathon judges, Phase 4.6 makes ForgeHive easy to inspect: enter a natural language building request, see the intent and reasoning trace, review candidate plans, and verify that safety boundaries prevent direct execution until Layer 5.
