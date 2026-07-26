import React from "react";

const STEPS = [
  "Situation",
  "Historical Plan",
  "Selected Actions",
  "Outcome",
  "Reward",
  "Stored Memory",
];

function actionLabel(action) {
  const labels = {
    lighting_adjustment: "Lighting",
    hvac_setpoint_adjustment: "HVAC setback",
    ventilation_adjustment: "Ventilation",
    preconditioning_schedule: "Preconditioning",
    carbon_schedule_shift: "Carbon shift",
    hvac_shutdown: "HVAC shutdown",
  };
  return labels[action] || String(action || "").replaceAll("_", " ");
}

export default function ExperienceTimeline({ experienceGraph }) {
  const selected = experienceGraph?.preferredHistoricalPlan || "Current plan";
  const reward = experienceGraph?.averageReward ?? "n/a";
  const preferredActions = (experienceGraph?.actionsToPrefer || []).slice(0, 2).map(actionLabel);
  const values = {
    Situation: `${experienceGraph?.similarExperiencesFound ?? 0} similar cases`,
    "Historical Plan": selected,
    "Selected Actions": preferredActions.join(", ") || "Safety-checked actions",
    Outcome: experienceGraph?.successRate != null ? `${Math.round(Number(experienceGraph.successRate) * 100)}% success` : "Simulation result",
    Reward: String(reward),
    "Stored Memory": experienceGraph?.experienceUpdated ? "Future Decisions Improved" : "Awaiting outcome",
  };

  return (
    <div className="experience-timeline" aria-label="Experience Graph mini graph">
      {STEPS.map((step, index) => (
        <React.Fragment key={step}>
          <div className="experience-step">
            <span>{step}</span>
            <strong>{values[step]}</strong>
          </div>
          {index < STEPS.length - 1 && <div className="experience-arrow">-&gt;</div>}
        </React.Fragment>
      ))}
    </div>
  );
}
