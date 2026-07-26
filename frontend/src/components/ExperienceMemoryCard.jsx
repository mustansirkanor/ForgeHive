import React from "react";
import { Database } from "lucide-react";

export default function ExperienceMemoryCard({ memory }) {
  const top = memory?.topStrategies?.[0] || {};
  return (
    <section className="experience-memory-card">
      <div className="memory-card-head">
        <Database size={19} />
        <div>
          <span>Experience Graph</span>
          <strong>{memory?.totalExperiences ?? 0} learned experiences</strong>
        </div>
      </div>
      <div className="memory-card-grid">
        <div>
          <span>Best Historical Strategy</span>
          <strong>{top.strategy || "No history yet"}</strong>
        </div>
        <div>
          <span>Average reward</span>
          <strong>{top.averageReward ?? "n/a"}</strong>
        </div>
        <div>
          <span>Confidence</span>
          <strong>{top.confidence ?? "n/a"}</strong>
        </div>
      </div>
    </section>
  );
}

