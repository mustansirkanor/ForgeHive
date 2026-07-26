import React, { useEffect, useMemo, useState } from "react";
import {
  BrainCircuit,
  CheckCircle2,
  Cpu,
  Database,
  Play,
  RotateCcw,
  Scale,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  UserRound,
  Wrench,
  XCircle,
} from "lucide-react";
import { askOperator, getFinalSummary, getScenarios, runScenario } from "./api";

const TABS = [
  { id: "template", label: "Ready Demo" },
  { id: "ask", label: "Ask ForgeHive" },
  { id: "simulate", label: "Simulate Action" },
];

function Badge({ tone = "good", children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

const NODE_ICONS = {
  request: UserRound,
  llm: BrainCircuit,
  actions: SlidersHorizontal,
  simulation: Cpu,
  ranking: Scale,
  safety: ShieldCheck,
  idf: Wrench,
  learning: Database,
};

function actionText(action) {
  if (!action) return "No action payload returned.";
  const parameters = Object.entries(action.parameters || {})
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join("-") : value}`)
    .join(", ");
  return `${action.actionType || "action"} on ${action.target || "unknown target"}${parameters ? ` (${parameters})` : ""}`;
}

function actionExplanation(action) {
  const params = action?.parameters || {};
  const target = String(action?.target || "the affected area").replaceAll("_", " ");
  if (action?.actionType === "hvac_setpoint_adjustment" && params.cooling_setpoint_c != null) {
    return `Cool ${target} to ${params.cooling_setpoint_c} C`;
  }
  if (action?.actionType === "ventilation_adjustment" && params.ventilation_multiplier != null) {
    return `Increase fresh air in ${target} by ${Math.round((params.ventilation_multiplier - 1) * 100)}%`;
  }
  if (action?.actionType === "lighting_adjustment" && params.lighting_level_percent != null) {
    return `Set lighting in ${target} to ${params.lighting_level_percent}%`;
  }
  if (action?.actionType === "preconditioning_schedule") {
    const nextMeeting = params.next_meeting_minutes;
    const restore = params.restore_minutes_before_meeting;
    if (nextMeeting != null && restore != null) {
      return `Restore comfort, lighting, and fresh air ${restore} minutes before the meeting in ${nextMeeting} minutes`;
    }
    return `Schedule comfort recovery before the next meeting`;
  }
  return action?.description || actionText(action);
}

function findTraceNode(result, id, fallbackIndex) {
  const trace = result?.decisionNodes || [];
  return trace.find((node) => node.id === id) || trace[fallbackIndex] || {};
}

function buildWorkflowNodes(result) {
  if (!result) return [];

  const selected = result.selectedBundle || {};
  const safety = result.safety || {};
  const twin = result.digitalTwin || {};
  const idf = result.idfAdapter || {};
  const learning = result.learning || {};
  const provider = result.provider || {};
  const candidates = result.candidateBundles || [];
  const ranked = result.rankedCandidates || [];
  const allCandidateActions = candidates.flatMap((candidate) => candidate.actions || []);
  const approvedActions = safety.approvedActions || (safety.approved === false ? [] : selected.actions || []);
  const blockedActions = safety.blockedActions || [];
  const candidateActions = selected.actions || [...approvedActions, ...blockedActions];
  const approved = safety.approved !== false;
  const traces = {
    request: findTraceNode(result, "request", 0),
    llm: findTraceNode(result, "llm", 1),
    actions: findTraceNode(result, "actions", 2),
    simulation: findTraceNode(result, "simulation", 3),
    safety: findTraceNode(result, "safety", 4),
    idf: findTraceNode(result, "idf", 5),
    learning: findTraceNode(result, "learning", 6),
  };

  return [
    {
      id: "request",
      title: "User request",
      kicker: "TRIGGER",
      status: "complete",
      summary: result.userMessage || traces.request.summary || "Request received",
      plainText: `ForgeHive received: "${result.userMessage || "Building request"}"`,
      input: ["Natural-language building command"],
      decision: "Forward the request to the autonomy planner.",
      output: [result.userMessage || "Request accepted"],
    },
    {
      id: "llm",
      title: "LLM planner",
      kicker: "OLLAMA",
      status: "complete",
      summary: selected.name || "Candidate bundle generated",
      plainText: `${provider.selectedProvider || "The planner"}${provider.model ? ` using ${provider.model}` : ""} created ${candidates.length || 1} possible way${candidates.length === 1 ? "" : "s"} to handle the request.`,
      input: [result.userMessage || "Building request", `Provider: ${provider.selectedProvider || "ollama"}`],
      decision: selected.rationale || traces.llm.summary || "Generated and ranked candidate control strategies.",
      output: [`Selected bundle: ${selected.name || "unknown"}`, ...(traces.llm.details || []).filter((detail) => !detail.toLowerCase().includes("selected"))],
    },
    {
      id: "actions",
      title: "Candidate plans",
      kicker: "OPTIONS",
      status: "complete",
      summary: `${candidates.length || 1} plan${candidates.length === 1 ? "" : "s"} proposed`,
      plainText: candidates.length > 1
        ? `The AI proposed ${candidates.length} complete plans: ${candidates.map((candidate) => candidate.name).join(", ")}. ForgeHive tested each one before choosing.`
        : candidates.length === 1
          ? `The AI produced one complete plan: ${candidates[0].name}. ForgeHive still simulated and safety-checked it, but there was no second valid plan to compare.`
        : `The AI proposed ${candidateActions.length} building action${candidateActions.length === 1 ? "" : "s"} for testing.`,
      input: [`Generated by: ${provider.selectedProvider || "planner"}`],
      decision: "Keep the AI-generated plans separate so every option can be simulated and compared.",
      output: candidates.length
        ? candidates.map((candidate) => `${candidate.name}: ${(candidate.actions || []).map(actionText).join("; ")}`)
        : candidateActions.length ? candidateActions.map(actionText) : ["No control action returned"],
      actions: allCandidateActions.length ? allCandidateActions : candidateActions,
    },
    {
      id: "simulation",
      title: "EnergyPlus",
      kicker: "DIGITAL TWIN",
      status: "complete",
      summary: `${twin.energySavedPercent ?? 0}% energy, ${twin.comfortStatus || "safe"}`,
      plainText: `EnergyPlus tested ${ranked.length || candidates.length || 1} possible plan${(ranked.length || candidates.length) === 1 ? "" : "s"} inside the digital building model. Nothing was sent to a real building.`,
      input: candidates.length ? candidates.map((candidate) => candidate.name) : ["Candidate bundle"],
      decision: traces.simulation.summary || "Simulate the candidate controls before approval.",
      output: [
        `Energy saved: ${twin.energySavedPercent ?? 0}%`,
        `Carbon reduced: ${twin.carbonReducedPercent ?? 0}%`,
        `Comfort result: ${twin.comfortStatus || "Safe"}`,
      ],
    },
    {
      id: "ranking",
      title: "Plan selection",
      kicker: "RL + KNOWLEDGE",
      status: "complete",
      summary: selected.name || "Best safe plan selected",
      plainText: ranked.length > 1
        ? `ForgeHive compared the simulated results, its learned history, and relevant building knowledge. It chose ${selected.name} over ${ranked.filter((item) => !item.selected).map((item) => item.name).join(", ") || "the other options"}.`
        : ranked.length === 1
          ? `Only one complete plan passed request alignment. RL and the knowledge graph scored it, but they did not choose between competing plans.`
        : `ForgeHive chose ${selected.name || "the safest plan"} after comparing expected comfort, safety, and building impact.`,
      input: ranked.length ? ranked.map((item) => `${item.name}: rank ${item.rank}`) : ["Simulated candidate results"],
      decision: selected.rankingReason || "Choose the highest-ranked plan that simulated successfully and preserved safety.",
      output: [
        `Selected: ${selected.name || "safe no-action"}`,
        ...ranked.map((item) => (
          `${item.rank}. ${item.name}: total ${item.totalScore ?? "n/a"}, `
          + `learned-history prior ${item.banditPrior ?? "n/a"}, knowledge match ${item.knowledgeGraphScore ?? "n/a"}`
        )),
      ],
    },
    {
      id: "safety",
      title: "Safety Governor",
      kicker: "POLICY GATE",
      status: approved ? "complete" : "rejected",
      summary: approved ? `${approvedActions.length} approved, ${blockedActions.length} blocked` : "Execution blocked",
      plainText: approved
        ? `The Safety Governor checked comfort limits, lighting safety, air quality, and anomalies. It allowed ${approvedActions.length} action${approvedActions.length === 1 ? "" : "s"}.`
        : `The Safety Governor stopped the plan, so ForgeHive made no building-model changes.`,
      input: candidateActions.length ? candidateActions.map(actionText) : ["Simulated candidate plan"],
      decision: safety.summary || traces.safety.summary || (approved ? "Plan is within safety constraints." : "Plan violated a safety constraint."),
      output: [
        `Comfort bounds: checked`,
        `IAQ / CO2 risk: checked`,
        `Real building execution: false`,
        ...approvedActions.map((action) => `APPROVED: ${actionText(action)}`),
        ...blockedActions.map((action) => `BLOCKED: ${actionText(action)}`),
      ],
      actions: [...approvedActions, ...blockedActions],
    },
    {
      id: "idf",
      title: "IDF adapter",
      kicker: "MODEL EDIT",
      status: approved ? "complete" : "blocked",
      summary: approved ? `${idf.adapterChangeCount ?? idf.changeCount ?? 0} model changes applied` : "Skipped by safety gate",
      plainText: approved
        ? `ForgeHive changed only the EnergyPlus digital twin: ${(approvedActions || []).map(actionExplanation).join("; ") || "the approved plan was applied"}.`
        : "No action was applied because the plan did not pass safety review.",
      input: approvedActions.length ? approvedActions.map(actionText) : ["No approved actions"],
      decision: approved ? "Convert approved controls into EnergyPlus IDF model changes." : "Do not apply blocked controls.",
      output: approved
        ? [
            `Lighting changed: ${Boolean(idf.lightingAppliedInIDF)}`,
            `HVAC changed: ${Boolean(idf.hvacSetpointAppliedInIDF)}`,
            `Ventilation changed: ${Boolean(idf.ventilationAppliedInIDF)}`,
            `IDF change count: ${idf.adapterChangeCount ?? idf.changeCount ?? 0}`,
          ]
        : ["No IDF mutation performed"],
      actions: approvedActions,
    },
    {
      id: "learning",
      title: "Learning update",
      kicker: "MEMORY",
      status: "complete",
      summary: learning.selfCorrectionSummary || "Run outcome recorded",
      plainText: learning.selfCorrectionSummary
        ? `After seeing the result, ForgeHive recorded this lesson: ${learning.selfCorrectionSummary}.`
        : "ForgeHive recorded the outcome so future plan selection can use what happened in this run.",
      input: [approved ? "Approved simulation outcome" : "Blocked safety outcome"],
      decision: learning.selfCorrectionSummary || "Record the outcome for future ranking.",
      output: [
        `Memory updated: ${Boolean(learning.memoryUpdated)}`,
        `Bandit updated: ${Boolean(learning.banditUpdated)}`,
        `Knowledge graph updated: ${Boolean(learning.knowledgeGraphUpdated)}`,
      ],
    },
  ];
}

function formatPercent(value) {
  if (value == null || value === "") return "n/a";
  const number = Number(value);
  if (Number.isNaN(number)) return String(value);
  return `${number.toFixed(number >= 10 ? 1 : 2)}%`;
}

function shortAction(action) {
  const text = actionExplanation(action);
  return text.endsWith(".") ? text.slice(0, -1) : text;
}

function getSelectedRank(result) {
  return (result?.rankedCandidates || []).find((candidate) => candidate.selected) || result?.rankedCandidates?.[0] || {};
}

function AutonomySnapshot({ result }) {
  const provider = result.provider || {};
  const safety = result.safety || {};
  const twin = result.digitalTwin || {};
  const learning = result.learning || {};
  const selected = result.selectedBundle || {};
  const selectedRank = getSelectedRank(result);
  const actions = safety.approvedActions?.length ? safety.approvedActions : selected.actions || [];

  const cards = [
    {
      label: "AI planner",
      title: provider.fallbackUsed ? "Fallback protected the run" : `${provider.selectedProvider || "LLM"} planned live`,
      body: provider.fallbackUsed
        ? "The backend could not rely on the live provider, so it used the deterministic safe path."
        : `Generated ${result.candidateBundles?.length || 0} candidate plan(s), then passed them to simulation.`,
      icon: BrainCircuit,
      tone: provider.fallbackUsed ? "warn" : "good",
    },
    {
      label: "RL bandit",
      title: learning.banditUpdated ? "Learned from this outcome" : "Used learned history",
      body: selectedRank.banditPrior != null
        ? `The selected strategy carried a learned-history prior of ${selectedRank.banditPrior}.`
        : "The ranker considered stored strategy reward history.",
      icon: Scale,
      tone: "rl",
    },
    {
      label: "Knowledge graph",
      title: learning.knowledgeGraphUpdated ? "KG updated after execution" : "KG checked relevance",
      body: selectedRank.knowledgeGraphScore != null
        ? `Matched the request to building concepts with KG score ${selectedRank.knowledgeGraphScore}.`
        : "Matched requested issues to relevant equipment, actions, and outcomes.",
      icon: Database,
      tone: "kg",
    },
    {
      label: "Safety",
      title: safety.approved === false ? "Blocked before execution" : "Approved digital-twin change",
      body: safety.approved === false
        ? "No EnergyPlus model edit was applied because the policy gate rejected the plan."
        : `${actions.length} action(s) passed comfort, IAQ, and real-building-execution checks.`,
      icon: ShieldCheck,
      tone: safety.approved === false ? "bad" : "good",
    },
  ];

  return (
    <div className="autonomy-snapshot">
      <section className="story-hero">
        <div>
          <p className="eyebrow">Demo story</p>
          <h2>{safety.approved === false ? "ForgeHive protected the building" : "ForgeHive made an autonomous digital-twin decision"}</h2>
          <p>
            It understood the request, created candidate plans, tested them in EnergyPlus, ranked them using simulation reward plus RL history and KG relevance, then let the Safety Governor decide whether anything could change.
          </p>
        </div>
        <div className="chosen-action">
          <span>Chosen action</span>
          <strong>{actions.length ? actions.map(shortAction).join("; ") : "No safe action"}</strong>
          <small>{twin.realBuildingExecution ? "Real building" : "Digital twin only"}</small>
        </div>
      </section>

      <div className="feature-grid">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <article className={`feature-card ${card.tone}`} key={card.label}>
              <Icon size={21} />
              <span>{card.label}</span>
              <strong>{card.title}</strong>
              <p>{card.body}</p>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function CandidatePlans({ result }) {
  const ranked = result?.rankedCandidates || [];
  const candidates = result?.candidateBundles || [];
  if (!ranked.length && !candidates.length) return null;

  const rows = ranked.length
    ? ranked
    : candidates.map((candidate, index) => ({
        rank: index + 1,
        name: candidate.name,
        selected: candidate.id === result?.selectedBundle?.id,
        energySavedPercent: candidate.energySavedPercent,
        comfortStatus: candidate.comfortStatus,
        totalScore: candidate.score,
        banditPrior: "n/a",
        knowledgeGraphScore: "n/a",
        actions: candidate.actions,
      }));

  return (
    <section className="candidate-panel">
      <div className="panel-title">
        <div>
          <p className="eyebrow">AI options</p>
          <h3>Plans ForgeHive compared</h3>
        </div>
        <Badge tone="neutral">{rows.length} candidate{rows.length === 1 ? "" : "s"}</Badge>
      </div>
      <div className="candidate-list">
        {rows.map((candidate) => {
          const source = candidates.find((item) => item.name === candidate.name) || {};
          const actions = candidate.actions || source.actions || [];
          return (
            <article className={candidate.selected ? "candidate-card selected" : "candidate-card"} key={`${candidate.rank}-${candidate.name}`}>
              <div className="candidate-rank">
                <span>#{candidate.rank}</span>
                {candidate.selected && <Badge>Selected</Badge>}
              </div>
              <strong>{candidate.name}</strong>
              <p>{actions.length ? actions.map(shortAction).join("; ") : source.rationale || candidate.reason || "Candidate plan"}</p>
              <div className="candidate-proof">
                <span>Energy {formatPercent(candidate.energySavedPercent)}</span>
                <span>Comfort {candidate.comfortStatus || "n/a"}</span>
                <span>RL {candidate.banditPrior ?? "n/a"}</span>
                <span>KG {candidate.knowledgeGraphScore ?? "n/a"}</span>
                <span>Total {candidate.totalScore ?? "n/a"}</span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ExplanationSteps({ result }) {
  const fallbackSteps = buildWorkflowNodes(result).map((node) => ({ title: node.title, text: node.plainText }));
  const steps = result?.explanationSteps?.length ? result.explanationSteps : fallbackSteps;
  return (
    <section className="explain-panel">
      <div className="panel-title">
        <div>
          <p className="eyebrow">Plain-English explanation</p>
          <h3>What happened in this run</h3>
        </div>
      </div>
      <div className="explain-steps">
        {steps.map((step, index) => (
          <article key={`${step.title}-${index}`}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <p>{step.text}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function ResultPanel({ result }) {
  const nodes = useMemo(() => buildWorkflowNodes(result), [result]);
  const [selectedNodeId, setSelectedNodeId] = useState("request");
  const [replayKey, setReplayKey] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    setSelectedNodeId(result ? "request" : "");
    setReplayKey((current) => current + 1);
  }, [result]);

  useEffect(() => {
    if (!result || nodes.length === 0) return undefined;
    setIsPlaying(true);
    const timers = nodes.map((node, index) => window.setTimeout(() => {
      setSelectedNodeId(node.id);
      if (index === nodes.length - 1) setIsPlaying(false);
    }, index * 650));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [nodes, replayKey, result]);

  if (!result) {
    return (
      <section className="result empty">
        <h2>No run yet</h2>
        <p>Run a template, ask an action, or simulate a building event to see ForgeHive respond.</p>
      </section>
    );
  }

  const safety = result.safety || {};
  const twin = result.digitalTwin || {};
  const selected = result.selectedBundle || {};
  const provider = result.provider || {};
  const selectedNode = nodes.find((node) => node.id === selectedNodeId) || nodes[0];

  return (
    <section className={safety.approved === false ? "result rejected" : "result"}>
      <div className="result-head">
        <div>
          <p className="eyebrow">Decision trace from backend</p>
          <h2>{safety.approved === false ? "Safety Governor blocked the action" : "ForgeHive decision flow"}</h2>
        </div>
        <Badge tone={safety.approved === false ? "bad" : "good"}>
          {safety.approved === false
            ? "Blocked"
            : result.mode === "live"
              ? provider.strictRealLLM ? "Live autonomous run" : "Safe fallback run"
              : "Example replay"}
        </Badge>
      </div>

      <div className="run-summary">
        <div>
          <span>User asked</span>
          <strong>{result.userMessage}</strong>
        </div>
        <div>
          <span>ForgeHive chose</span>
          <strong>{(safety.approvedActions || []).map((action) => action.description || action.actionType).join("; ") || "No action selected"}</strong>
        </div>
        <div>
          <span>Safety result</span>
          <strong>{safety.approved === false ? "Rejected" : "Approved"}</strong>
        </div>
      </div>

      <AutonomySnapshot result={result} />
      <ExplanationSteps result={result} />
      <CandidatePlans result={result} />

      <div className="workflow-shell">
        <div className="workflow-toolbar">
          <div className="workflow-live"><span /> Execution complete</div>
          <button className="icon-command" onClick={() => setReplayKey((current) => current + 1)} title="Replay execution animation">
            {isPlaying ? <Play size={16} /> : <RotateCcw size={16} />} {isPlaying ? "Playing" : "Replay"}
          </button>
        </div>

        <div className="workflow-viewport" aria-label="ForgeHive agent execution graph">
          <div className="workflow-grid" key={replayKey}>
            {nodes.map((node, index) => {
              const Icon = NODE_ICONS[node.id] || Sparkles;
              const isSelected = selectedNode?.id === node.id;
              return (
                <React.Fragment key={node.id}>
                  <button
                    className={`workflow-node ${node.status} ${isSelected ? "selected" : ""}`}
                    style={{ "--delay": `${index * 180}ms` }}
                    onClick={() => setSelectedNodeId(node.id)}
                    aria-pressed={isSelected}
                  >
                    <span className="node-port input-port" />
                    <span className="workflow-node-icon"><Icon size={19} /></span>
                    <span className="workflow-node-copy">
                      <small>{node.kicker}</small>
                      <strong>{node.title}</strong>
                      <span>{node.summary}</span>
                    </span>
                    <span className={`node-state ${node.status}`}>
                      {node.status === "rejected" ? <XCircle size={14} /> : <CheckCircle2 size={14} />}
                      {node.status}
                    </span>
                    <span className="node-port output-port" />
                  </button>
                  {index < nodes.length - 1 && (
                    <div className={`workflow-edge ${node.status}`} style={{ "--delay": `${index * 180 + 100}ms` }} aria-hidden="true">
                      <span className="edge-packet" />
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {selectedNode && (
          <div className="node-inspector">
            <div className="inspector-head">
              <div>
                <span>{selectedNode.kicker}</span>
                <h3>{selectedNode.title}</h3>
              </div>
              <Badge tone={selectedNode.status === "rejected" ? "bad" : selectedNode.status === "blocked" ? "neutral" : "good"}>
                {selectedNode.status}
              </Badge>
            </div>
            <div className="plain-explanation">
              <span>In plain English</span>
              <p>{selectedNode.plainText}</p>
            </div>
            <details className="technical-details">
              <summary>Show technical proof</summary>
              <div className="inspector-columns">
                <section>
                  <h4>Input</h4>
                  {(selectedNode.input || []).map((item) => <p key={item}>{item}</p>)}
                </section>
                <section className="decision-column">
                  <h4>Decision</h4>
                  <p>{selectedNode.decision}</p>
                </section>
                <section>
                  <h4>Output / action taken</h4>
                  {(selectedNode.output || []).map((item) => (
                    <p className={item.startsWith("BLOCKED:") ? "blocked-output" : ""} key={item}>{item}</p>
                  ))}
                </section>
              </div>
            </details>
          </div>
        )}
      </div>

      <div className="plain-outcome">
        <CheckCircle2 size={22} />
        <div>
          <strong>{result.plainOutcome || `The digital twin finished with comfort marked ${twin.comfortStatus || "Safe"}.`}</strong>
          <span>No real building equipment was controlled.</span>
        </div>
      </div>

      {safety.blockedActions?.length > 0 && (
        <div className="blocked-box">
          <strong>Blocked action</strong>
          <code>{JSON.stringify(safety.blockedActions[0], null, 2)}</code>
        </div>
      )}
    </section>
  );
}

function TemplatePage({ summary, onRun }) {
  return (
    <section className="page-grid">
      <div className="hero-card">
        <p className="eyebrow">Ready-made judge template</p>
        <h1>ForgeHive building autonomy demo</h1>
        <p>
          One-click walkthrough using the completed Layer 5.7 and Layer 6 artifacts. This is the clean version to show first.
        </p>
        <div className="hero-actions">
          <button className="primary" onClick={onRun}>Run Ready Demo</button>
          <Badge>100/100 Ready</Badge>
          <Badge>Ollama + EnergyPlus Proof</Badge>
        </div>
      </div>

      <div className="side-card">
        <h2>What judges see</h2>
        <ul>
          <li>User request enters ForgeHive.</li>
          <li>Ollama creates candidate actions.</li>
          <li>EnergyPlus simulates the options.</li>
          <li>Safety Governor approves safe plans only.</li>
          <li>ForgeHive acts only in the digital twin and learns.</li>
        </ul>
        <div className="score-line">
          <span>Readiness</span>
          <strong>{summary?.readinessScore ?? 100}/100</strong>
        </div>
      </div>
    </section>
  );
}

function AskPage({ defaultMessage, onAsk }) {
  const [message, setMessage] = useState(defaultMessage);
  const [mode, setMode] = useState("live");

  useEffect(() => setMessage(defaultMessage), [defaultMessage]);

  return (
    <section className="single-page">
      <div className="hero-card compact">
        <p className="eyebrow">Natural language action</p>
        <h1>Ask ForgeHive to do something</h1>
        <p>Describe what you want in normal language. ForgeHive will generate options, test them in EnergyPlus, choose safely, and explain what happened.</p>
      </div>

      <div className="form-card">
        <textarea value={message} onChange={(event) => setMessage(event.target.value)} />
        <div className="segmented">
          <button className={mode === "live" ? "active" : ""} onClick={() => setMode("live")}>Live autonomy</button>
          <button className={mode === "artifact" ? "active" : ""} onClick={() => setMode("artifact")}>Example replay</button>
        </div>
        <button className="primary wide" onClick={() => onAsk(message, mode)}>Ask ForgeHive</button>
      </div>
    </section>
  );
}

function SimulatePage({ scenarios, selectedScenarioId, setSelectedScenarioId, selectedScenario, onRun }) {
  return (
    <section className="page-grid">
      <div className="side-card scenario-list-card">
        <h2>Simulate real building events</h2>
        {scenarios.map((scenario) => (
          <button
            key={scenario.id}
            className={scenario.id === selectedScenarioId ? "scenario active" : "scenario"}
            onClick={() => setSelectedScenarioId(scenario.id)}
          >
            {scenario.title}
          </button>
        ))}
      </div>

      <div className="hero-card compact">
        <p className="eyebrow">Selected event</p>
        <h1>{selectedScenario?.title || "Choose a scenario"}</h1>
        <p>{selectedScenario?.user_message}</p>
        <div className="state-grid">
          {Object.entries(selectedScenario?.before_state || {}).map(([key, value]) => (
            <div key={key}>
              <span>{key.replaceAll("_", " ")}</span>
              <strong>{String(value)}</strong>
            </div>
          ))}
        </div>
        <div className="hero-actions">
          <button className="primary" onClick={() => onRun("artifact")}>Fast Simulation</button>
          <button className="secondary" onClick={() => onRun("live")}>Live Ollama + EnergyPlus</button>
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [tab, setTab] = useState("template");
  const [summary, setSummary] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState("empty_room");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [summaryData, scenarioData] = await Promise.all([getFinalSummary(), getScenarios()]);
        setSummary(summaryData);
        setScenarios(scenarioData);
      } catch (err) {
        setError(err.message);
      }
    }
    load();
  }, []);

  const selectedScenario = useMemo(
    () => scenarios.find((scenario) => scenario.id === selectedScenarioId) || scenarios[0],
    [scenarios, selectedScenarioId]
  );

  async function runDirect(payload, label) {
    setLoading(label);
    setError("");
    try {
      const directResult =
        payload.type === "scenario"
          ? await runScenario(payload.scenario_id, payload.mode)
          : await askOperator(payload.message, payload.mode);
      setResult(directResult);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  function runReadyDemo() {
    setTab("template");
    return runDirect({ type: "scenario", scenario_id: "empty_room", mode: "artifact" }, "Running ready-made demo.");
  }

  function runSelectedScenario(mode) {
    if (!selectedScenario) return;
    const label = mode === "live" ? "Running live Ollama + EnergyPlus digital twin. This may take 30-90 seconds." : "Running fast scenario simulation.";
    return runDirect({ type: "scenario", scenario_id: selectedScenario.id, mode }, label);
  }

  function askForgeHive(message, mode) {
    const label = mode === "live" ? "Running live Ollama + EnergyPlus digital twin. This may take 30-90 seconds." : "Asking ForgeHive using artifact replay.";
    return runDirect({ type: "operator", message, mode }, label);
  }

  return (
    <main>
      <nav className="topbar">
        <div>
          <strong>ForgeHive</strong>
          <span>EnergyPlus digital twin only</span>
        </div>
        <div className="tabs">
          {TABS.map((item) => (
            <button key={item.id} className={tab === item.id ? "active" : ""} onClick={() => setTab(item.id)}>
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      {error && <section className="notice bad">{error}</section>}
      {loading && <section className="notice">{loading}</section>}

      {tab === "template" && <TemplatePage summary={summary} onRun={runReadyDemo} />}
      {tab === "ask" && <AskPage defaultMessage={selectedScenario?.user_message || ""} onAsk={askForgeHive} />}
      {tab === "simulate" && (
        <SimulatePage
          scenarios={scenarios}
          selectedScenarioId={selectedScenarioId}
          setSelectedScenarioId={setSelectedScenarioId}
          selectedScenario={selectedScenario}
          onRun={runSelectedScenario}
        />
      )}

      <ResultPanel result={result} />
    </main>
  );
}
