# Layer 4.5 LLM Provider Setup

ForgeHive Layer 4.5 supports real provider integration with safe fallback:

```text
Ollama -> OpenRouter -> Mock
```

Layer 4 still does not execute actions. It only generates candidate action bundles and reasoning. Layer 5 will simulate, rank, approve, execute, and learn.

Phase 4.6 builds on this provider layer with a natural language building operator. See `docs/LAYER_4_6_NATURAL_LANGUAGE_OPERATOR.md` for the intent routing, explainable cognitive trace, demo scenarios, and Layer 5 handoff.

## Environment Variables

```env
FORGEHIVE_LLM_MODE=auto
FORGEHIVE_LLM_PROVIDER_PRIORITY=ollama,openrouter,mock

OLLAMA_BASE_URL=http://localhost:11434
FORGEHIVE_OLLAMA_MODEL=llama3.1:8b
FORGEHIVE_OLLAMA_TIMEOUT_SECONDS=90

OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS=60

FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS=140
```

Supported modes:

- `mock`: deterministic local fallback, no network or API key required.
- `ollama`: local Ollama first, mock fallback if it fails.
- `openrouter`: OpenRouter first, mock fallback if it fails.
- `auto`: provider priority order from `FORGEHIVE_LLM_PROVIDER_PRIORITY`.
- `disabled`: no LLM call; candidate generation can still use deterministic fallback.

Timeout tuning:

- `FORGEHIVE_OLLAMA_TIMEOUT_SECONDS`: per-call Ollama timeout, default `90`.
- `FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS`: per-call OpenRouter timeout, default `60`.
- `FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS`: soft total provider-selection timeout, default `140`.
- Ollama retries once after a timeout, then ForgeHive continues to the next provider.

## Ollama Setup

Install and run Ollama locally, then pull the model:

```powershell
ollama pull llama3.1:8b
```

Default endpoint:

```text
http://localhost:11434/api/generate
```

## OpenRouter Setup

Create an OpenRouter API key and set:

```env
OPENROUTER_API_KEY=<set in .env or deployment secrets>
```

Default model:

```text
meta-llama/llama-3.1-8b-instruct
```

Security warning: never commit `OPENROUTER_API_KEY`. Keep real keys in `.env`, deployment secrets, or your hosting provider secret store.

## Deployment Recommendations

Local/dev with every provider available:

```env
FORGEHIVE_LLM_MODE=auto
FORGEHIVE_LLM_PROVIDER_PRIORITY=ollama,openrouter,mock
OLLAMA_BASE_URL=http://localhost:11434
FORGEHIVE_OLLAMA_MODEL=llama3.1:8b
FORGEHIVE_OLLAMA_TIMEOUT_SECONDS=90
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS=60
FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS=140
```

Local/dev without network or keys:

```env
FORGEHIVE_LLM_MODE=mock
```

Railway/backend deployment until Ollama is hosted separately:

```env
FORGEHIVE_LLM_MODE=auto
FORGEHIVE_LLM_PROVIDER_PRIORITY=openrouter,mock
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS=60
FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS=140
```

Final demo with local Ollama primary and OpenRouter fallback:

```env
FORGEHIVE_LLM_MODE=auto
FORGEHIVE_LLM_PROVIDER_PRIORITY=ollama,openrouter,mock
OLLAMA_BASE_URL=http://localhost:11434
FORGEHIVE_OLLAMA_MODEL=llama3.1:8b
FORGEHIVE_OLLAMA_TIMEOUT_SECONDS=90
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
FORGEHIVE_OPENROUTER_TIMEOUT_SECONDS=60
FORGEHIVE_LLM_TOTAL_TIMEOUT_SECONDS=140
```

Set `OPENROUTER_API_KEY` only in `.env` or deployment secrets. Never commit it.

## Safety Boundary

LLMs generate candidate bundles only. They cannot execute actions, call EnergyPlus directly, or bypass validation. Candidate bundles must pass Layer 4 schema validation, future Layer 5 simulation/ranking, and Safety Governor approval before execution.

## Real Provider Schema Contract

Real providers must return only JSON with a top-level `candidate_bundles` list. Each candidate bundle must contain non-empty `actions`, `expected_outcome` as an object, and `constraints` as a list. ForgeHive hardens real provider output before validation so repairable Ollama/OpenRouter responses are accepted instead of falling through to mock.

Allowed canonical action types:

- `lighting_adjustment`
- `hvac_setpoint_adjustment`
- `ventilation_adjustment`
- `carbon_schedule_shift`
- `strategy_mode`
- `no_direct_control_change`

Common alias repairs include:

- occupancy controls -> `strategy_mode`
- lighting controls / dim lights -> `lighting_adjustment`
- HVAC / setpoint / temperature adjustments -> `hvac_setpoint_adjustment`
- IAQ / air quality / ventilation controls -> `ventilation_adjustment`
- carbon scheduling / load shift / carbon shift -> `carbon_schedule_shift`
- do nothing / no action -> `no_direct_control_change`

Schema repair is needed because local and hosted LLMs often produce close-but-not-exact JSON, such as `expected_outcome` as a string or action types like `occupancy_based_control`. ForgeHive normalizes safe aliases, converts repairable fields, drops unknown actions, and accepts a provider if at least one valid normalized bundle remains. Mock is the final fallback only when real providers are unreachable or truly invalid.

Run the real-provider contract check:

```powershell
python -m backend.app.cognitive.test_real_provider_contract
```
