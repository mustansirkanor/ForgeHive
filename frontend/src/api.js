const API_BASE = import.meta.env.VITE_FORGEHIVE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json();
}

export function getFinalSummary() {
  return request("/api/final-summary");
}

export function getScenarios() {
  return request("/api/scenarios");
}

export function runScenario(scenarioId, mode) {
  return request("/api/scenarios/run", {
    method: "POST",
    body: JSON.stringify({ scenario_id: scenarioId, mode }),
  });
}

export function askOperator(message, mode) {
  return request("/api/operator/ask", {
    method: "POST",
    body: JSON.stringify({ message, mode }),
  });
}

export function getJudgeSummary() {
  return request("/api/judge-summary");
}

export function getDemoScript() {
  return request("/api/demo-script");
}
