import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from backend.app.demo_api.artifact_loader import (
    build_final_summary,
    build_frontend_demo_response,
    list_artifacts,
    read_text,
)
from backend.app.demo_api.scenarios import get_scenario, get_scenarios
from backend.app.experience.experience_api import get_experience_memory_summary, query_experience_memory


def health() -> dict:
    return {"status": "ok", "project": "ForgeHive", "realBuildingExecution": False}


RUNS: dict[str, dict] = {}


def run_demo_scenario(scenario_id: str, mode: str = "artifact") -> dict:
    scenario = get_scenario(scenario_id)
    if not scenario:
        raise ValueError(f"Unknown scenario_id: {scenario_id}")
    return run_demo_message(scenario["user_message"], mode=mode, scenario=scenario)


def run_demo_message(message: str, mode: str = "artifact", scenario: dict | None = None) -> dict:
    if mode == "live":
        from backend.app.closed_loop.real_llm_full_loop import run_real_ollama_full_loop_demo

        raw = {"layer57": run_real_ollama_full_loop_demo(message)}
        return build_frontend_demo_response(raw=raw, scenario=scenario, user_message=message, mode="live")
    return build_frontend_demo_response(scenario=scenario, user_message=message, mode="artifact")


def start_run(payload: dict) -> dict:
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {
        "runId": run_id,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    }

    def worker() -> None:
        try:
            RUNS[run_id].update({"status": "running", "progress": 15})
            run_type = payload.get("type", "operator")
            mode = payload.get("mode", "artifact")
            if run_type == "scenario":
                result = run_demo_scenario(payload.get("scenario_id", ""), mode)
            else:
                result = run_demo_message(payload.get("message", ""), mode)
            RUNS[run_id].update({"status": "complete", "progress": 100, "result": result})
        except Exception as exc:
            RUNS[run_id].update({"status": "failed", "progress": 100, "error": str(exc)})

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return RUNS[run_id]


def get_run(run_id: str) -> dict:
    if run_id not in RUNS:
        raise ValueError(f"Unknown run_id: {run_id}")
    return RUNS[run_id]


try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field

    class ScenarioRunRequest(BaseModel):
        scenario_id: str
        mode: str = "artifact"

    class OperatorAskRequest(BaseModel):
        message: str
        mode: str = "artifact"

    class RunStartRequest(BaseModel):
        type: str = "operator"
        mode: str = "artifact"
        scenario_id: str | None = None
        message: str | None = None

    class ExperienceQueryRequest(BaseModel):
        event_type: str
        goal: str
        building_state: dict = Field(default_factory=dict)

    app = FastAPI(title="ForgeHive Layer 7 Demo API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def api_health() -> dict:
        return health()

    @app.get("/api/final-summary")
    def api_final_summary() -> dict:
        return build_final_summary()

    @app.get("/api/scenarios")
    def api_scenarios() -> list[dict]:
        return get_scenarios()

    @app.post("/api/scenarios/run")
    def api_run_scenario(request: ScenarioRunRequest) -> dict:
        try:
            return run_demo_scenario(request.scenario_id, request.mode)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/operator/ask")
    def api_operator_ask(request: OperatorAskRequest) -> dict:
        return run_demo_message(request.message, request.mode)

    @app.post("/api/runs")
    def api_start_run(request: RunStartRequest) -> dict:
        return start_run(request.model_dump())

    @app.get("/api/runs/{run_id}")
    def api_get_run(run_id: str) -> dict:
        try:
            return get_run(run_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/artifacts")
    def api_artifacts() -> dict:
        return list_artifacts()

    @app.get("/api/experience-memory")
    def api_experience_memory() -> dict:
        return get_experience_memory_summary()

    @app.post("/api/experience/query")
    def api_experience_query(request: ExperienceQueryRequest) -> dict:
        return query_experience_memory(request.model_dump())

    @app.get("/api/judge-summary")
    def api_judge_summary() -> dict:
        from backend.app.demo_api.artifact_loader import FINAL_DIR

        return {"project": "ForgeHive", "realBuildingExecution": False, "content": read_text(FINAL_DIR / "forgehive_judge_summary.md")}

    @app.get("/api/demo-script")
    def api_demo_script() -> dict:
        from backend.app.demo_api.artifact_loader import FINAL_DIR

        return {"project": "ForgeHive", "realBuildingExecution": False, "content": read_text(FINAL_DIR / "forgehive_demo_script.md")}

except ImportError:
    app = None


class DemoRequestHandler(BaseHTTPRequestHandler):
    def _send(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_OPTIONS(self) -> None:
        self._send({})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        from backend.app.demo_api.artifact_loader import FINAL_DIR

        routes = {
            "/api/health": health,
            "/api/final-summary": build_final_summary,
            "/api/scenarios": get_scenarios,
            "/api/artifacts": list_artifacts,
            "/api/experience-memory": get_experience_memory_summary,
            "/api/judge-summary": lambda: {"project": "ForgeHive", "realBuildingExecution": False, "content": read_text(FINAL_DIR / "forgehive_judge_summary.md")},
            "/api/demo-script": lambda: {"project": "ForgeHive", "realBuildingExecution": False, "content": read_text(FINAL_DIR / "forgehive_demo_script.md")},
        }
        if path.startswith("/api/runs/"):
            try:
                self._send(get_run(path.rsplit("/", 1)[-1]))
            except ValueError as exc:
                self._send({"error": str(exc)}, status=404)
            return
        if path not in routes:
            self._send({"error": "not_found"}, status=404)
            return
        self._send(routes[path]())

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        payload = self._read_json()
        try:
            if path == "/api/scenarios/run":
                self._send(run_demo_scenario(payload.get("scenario_id", ""), payload.get("mode", "artifact")))
            elif path == "/api/operator/ask":
                self._send(run_demo_message(payload.get("message", ""), payload.get("mode", "artifact")))
            elif path == "/api/runs":
                self._send(start_run(payload))
            elif path == "/api/experience/query":
                self._send(query_experience_memory(payload))
            else:
                self._send({"error": "not_found"}, status=404)
        except ValueError as exc:
            self._send({"error": str(exc)}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    if app is not None:
        try:
            import uvicorn

            uvicorn.run("backend.app.demo_api.server:app", host="127.0.0.1", port=8000, reload=False)
            return
        except ImportError:
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 8000), DemoRequestHandler)
    print("ForgeHive demo API running at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
