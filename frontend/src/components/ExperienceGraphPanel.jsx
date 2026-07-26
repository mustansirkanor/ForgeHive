import React from "react";
import { AlertTriangle, BrainCircuit, CheckCircle2, History } from "lucide-react";
import ExperienceTimeline from "./ExperienceTimeline";

function PillList({ items, emptyText }) {
  const values = (items || []).filter(Boolean);
  if (!values.length) return <p className="experience-empty">{emptyText}</p>;
  return (
    <div className="experience-pills">
      {values.map((item) => <span key={item}>{item}</span>)}
    </div>
  );
}

export default function ExperienceGraphPanel({ result, memory }) {
  const graph = result?.experienceGraph || {};
  const topStrategy = graph.topStrategies?.[0] || memory?.topStrategies?.[0] || {};
  const failures = graph.failurePatterns || memory?.failurePatterns || [];
  const lessons = graph.lessonsLearned || memory?.recentLessons || [];
  const similar = graph.similarExperiencesFound ?? 0;

  return (
    <section className="experience-panel">
      <div className="panel-title">
        <div>
          <p className="eyebrow">Experience Graph</p>
          <h3>Similar Past Situations</h3>
        </div>
        <span className="experience-status">
          <History size={15} />
          {similar > 0 ? "Prior used" : "Exploring safely"}
        </span>
      </div>

      <p className="experience-copy">
        ForgeHive remembers previous EnergyPlus-tested decisions. When a similar building situation appears again, it retrieves past successes and failures, gives the LLM and RL ranker better context, and still passes the final plan through the Safety Governor.
      </p>
      <p className="experience-copy strong">
        {similar > 0
          ? "ForgeHive has seen similar situations before and is using those experiences as a decision prior."
          : "No similar previous experience found. ForgeHive will explore safely using simulation and safety checks."}
      </p>

      <div className="experience-overview">
        <div>
          <span>Total learned experiences</span>
          <strong>{graph.totalExperiences ?? memory?.totalExperiences ?? 0}</strong>
        </div>
        <div>
          <span>Best Historical Strategy</span>
          <strong>{graph.preferredHistoricalPlan || topStrategy.strategy || "n/a"}</strong>
        </div>
        <div>
          <span>Average reward</span>
          <strong>{graph.averageReward ?? topStrategy.averageReward ?? "n/a"}</strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>{graph.confidence ?? topStrategy.confidence ?? "n/a"}</strong>
        </div>
        <div>
          <span>Similar cases found</span>
          <strong>{similar}</strong>
        </div>
      </div>

      <div className="experience-columns">
        <article>
          <BrainCircuit size={18} />
          <span>Actions to Prefer</span>
          <PillList items={graph.actionsToPrefer} emptyText="No preferred action memory yet." />
        </article>
        <article>
          <AlertTriangle size={18} />
          <span>Actions to Avoid</span>
          <PillList items={graph.actionsToAvoid || failures.map((item) => item.action_type)} emptyText="No failure memory yet." />
        </article>
        <article>
          <CheckCircle2 size={18} />
          <span>New Experience Stored</span>
          <strong>{graph.experienceUpdated ? graph.experienceId || "Stored" : "Not stored yet"}</strong>
          <p>{lessons[0] || "Future Decisions Improved"}</p>
        </article>
      </div>

      {failures.length > 0 && (
        <div className="failure-memory">
          <strong>Failure memory</strong>
          {failures.slice(0, 2).map((failure) => (
            <p key={`${failure.action_type}-${failure.failure_reason}`}>
              {failure.action_type}: {failure.avoidance_rule || failure.failure_reason}
            </p>
          ))}
        </div>
      )}

      <ExperienceTimeline experienceGraph={graph} />
    </section>
  );
}
