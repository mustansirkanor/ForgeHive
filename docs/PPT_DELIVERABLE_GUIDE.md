# ForgeHive PPT Deliverable Guide

Use this as the structure for your final presentation deck.

## Slide 1: Title

**ForgeHive: Autonomous Building Optimization With EnergyPlus Digital Twin**

Include:
- Your name/team
- Project name: ForgeHive
- One-line pitch: AI building operator that plans, simulates, safety-checks, executes in a digital twin, and learns from outcomes.

## Slide 2: Problem

Explain:
- Buildings waste energy when HVAC, lighting, and ventilation keep running after spaces become empty.
- Aggressive control can harm comfort, IAQ, or safety.
- Most dashboards only monitor; they do not safely decide, test, act, and learn.

## Slide 3: Solution

Explain:
- ForgeHive is an autonomous building-control agent.
- It accepts natural language requests.
- It generates candidate action bundles.
- It tests them in EnergyPlus.
- It ranks plans using reward, RL/Bandit history, Knowledge Graph, and Experience Graph memory.
- It executes only approved actions in the digital twin.

## Slide 4: System Architecture

Show the pipeline:

```text
User Request
  -> LLM Planner
  -> Knowledge Graph + Experience Graph
  -> Candidate Bundles
  -> EnergyPlus Simulation
  -> RL/Bandit Ranking
  -> Safety Governor
  -> IDF Adapter
  -> Digital Twin Execution
  -> Feedback Learning
  -> Stored Experience
```

Mention clearly:
- No real building equipment is controlled.
- Safety Governor remains final authority.

## Slide 5: Layer Summary

Include a simple table:

| Layer | What It Does |
|---|---|
| Layer 1 | EnergyPlus baseline and simulation proof |
| Layer 2 | Building intelligence, comfort, anomalies, memory |
| Layer 3 | Decision layer, RL/Bandit, Safety Governor |
| Layer 4 | LLM cognitive operator and MCP-style tools |
| Layer 5 | Closed-loop simulation, ranking, execution, learning |
| Layer 6 | Final audit and readiness scoring |
| Layer 7 | Frontend demo dashboard |
| Layer 8 | Experience Graph / episodic building memory |

## Slide 6: Demo Scenario

Use the recorded demo scenario:

**Prompt:**  
`The meeting room is empty now. Save energy but keep comfort safe.`

Show:
- User request
- Detected intent: empty room energy saving
- Candidate plans generated
- Selected plan
- Safety result
- Digital twin outcome

## Slide 7: Candidate Bundles

Show screenshots or bullets for:
- Candidate plans ForgeHive considered
- Actions such as:
  - lighting adjustment
  - HVAC setpoint adjustment
  - ventilation adjustment
  - preconditioning schedule, if applicable

Main point:
- ForgeHive compares options instead of directly executing the first LLM idea.

## Slide 8: EnergyPlus Simulation

Explain:
- Every candidate is tested in the EnergyPlus digital twin.
- Simulation estimates:
  - energy saved
  - carbon reduced
  - comfort status
  - anomaly count

Include screenshot from frontend if available.

## Slide 9: RL + Knowledge Graph Ranking

Explain:
- Ranking combines:
  - base reward score
  - bandit prior score
  - Knowledge Graph score
  - Experience Graph prior score
  - final safety/simulation penalties

Main point:
- ForgeHive selects the best simulated plan using both current performance and learned context.

## Slide 10: Safety Governor

Explain:
- Safety Governor checks comfort, IAQ, bounds, and execution rules.
- Unsafe actions are blocked.
- Real building execution remains false.

Include:
- Approved action screenshot for safe demo
- Optional rejected unsafe command screenshot if you want to show safety protection.

## Slide 11: IDF Adapter + Digital Twin Execution

Explain:
- Approved actions are translated into EnergyPlus IDF model changes.
- Execution happens only inside the digital twin.
- Output includes energy, carbon, comfort, and execution status.

Mention:
- `realBuildingExecution = false`
- `digitalTwinExecution = true`

## Slide 12: Experience Graph / Episodic Memory

Use this as the headline:

**ForgeHive does not relearn every building situation from scratch.**

Explain:
- It stores previous operational episodes:
  - situation
  - generated plans
  - simulated outcomes
  - selected plan
  - safety decision
  - execution result
  - reward
  - lessons learned
- On future similar scenarios, it retrieves relevant experiences.
- LLM and RL ranking use these experiences as an advisory prior.
- Safety still overrides history.

## Slide 13: Experience Graph Demo Proof

Show:
- Similar Past Situations
- Best Historical Strategy
- Actions to Prefer
- Actions to Avoid
- New Experience Stored
- Future Decisions Improved

Use frontend screenshots from the Experience Graph panel.

## Slide 14: Results

Include measured/demo values:
- Energy saved %
- Carbon reduced %
- Comfort status
- Safety approved/blocked status
- Memory updated
- Bandit updated
- Knowledge Graph updated
- Experience Graph updated

Use values from your final run/video.

## Slide 15: Final Audit / Readiness

Show:
- Backend audit passed, if available
- Frontend build passed
- Final readiness score
- Artifacts generated

If Python audit was not run on your machine, say:
- Frontend build passed.
- Backend test commands are prepared.
- Final backend audit should be run in an environment with Python installed.

## Slide 16: Deliverables

List:
- Source code
- Backend APIs
- React frontend dashboard
- Experience Graph JSON memory
- Docs
- Artifacts
- Final demo video
- README
- `.env.example`
- Final submission package/zip

## Slide 17: Conclusion

Use this closing message:

ForgeHive is a digital-twin autonomous building optimization system. It can understand natural language, generate candidate control plans, test them in EnergyPlus, rank them with learned intelligence, enforce safety, execute only in the digital twin, and remember outcomes through an Experience Graph for better future decisions.

## Must-Have Screenshots

Include these in the PPT:
- Main ForgeHive dashboard
- Candidate Bundles / Plans compared
- RL ranking section
- Safety Governor approval or rejection
- Digital twin outcome
- Experience Graph panel
- Final proof/readiness summary

## Must-Say Safety Line

Use this exact message somewhere:

**ForgeHive never controls real building equipment in this demo. All execution is limited to the EnergyPlus digital twin, and the Safety Governor remains the final authority.**

