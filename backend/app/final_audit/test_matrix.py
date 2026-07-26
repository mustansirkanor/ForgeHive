import json
import os
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "final_submission"
OUTPUT_FILE = OUTPUT_DIR / "forgehive_test_matrix.json"
TAIL_CHARS = 4000


TEST_MATRIX = {
    "Layer 1": [
        "backend.app.energyplus.test_runner",
        "backend.app.energyplus.test_parser",
        "backend.app.energyplus.test_comparison_api",
    ],
    "Layer 2": [
        "backend.app.intelligence.test_schemas",
        "backend.app.intelligence.test_state_extractor",
        "backend.app.intelligence.test_comfort_engine",
        "backend.app.intelligence.test_building_score",
        "backend.app.intelligence.test_anomaly_detector",
        "backend.app.intelligence.test_memory_engine",
        "backend.app.intelligence.test_intelligence_api",
    ],
    "Layer 3": [
        "backend.app.decision.test_safety_governor",
        "backend.app.decision.test_supervisor_bandit",
        "backend.app.decision.test_decision_api",
        "backend.app.decision.test_layer3_proof",
    ],
    "Layer 4": [
        "backend.app.cognitive.test_mcp_tool_registry",
        "backend.app.cognitive.test_llm_schema_repair",
        "backend.app.cognitive.test_provider_schema_normalizer",
        "backend.app.cognitive.test_real_provider_contract",
        "backend.app.cognitive.test_natural_language_operator",
        "backend.app.cognitive.test_cognitive_layer",
    ],
    "Layer 5": [
        "backend.app.closed_loop.test_bundle_simulator",
        "backend.app.closed_loop.test_reward_ranker",
        "backend.app.closed_loop.test_final_safety_gate",
        "backend.app.closed_loop.test_layer5_phase_1_3",
        "backend.app.closed_loop.test_digital_twin_executor",
        "backend.app.closed_loop.test_feedback_learner",
        "backend.app.closed_loop.test_layer5_phase_4_6",
        "backend.app.energyplus.test_idf_adapter",
        "backend.app.closed_loop.test_phase57_artifacts",
        "backend.app.closed_loop.test_phase57_real_llm_full_loop",
    ],
}


def redaction_values() -> list[str]:
    values = []
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if api_key:
        values.append(api_key)
    return values


def redact(text: str) -> str:
    redacted = text or ""
    for value in redaction_values():
        if value:
            redacted = redacted.replace(value, "[REDACTED_OPENROUTER_API_KEY]")
    return redacted


EXPLICIT_SKIP_MARKERS = (
    "TEST_SKIPPED",
    "pytest.skip",
    "Real provider unavailable; strict real LLM demo not proven.",
    "SKIPPED_TEST:",
)


def classify_test_result(command: str, return_code: int, stdout: str, stderr: str) -> str:
    combined = f"{stdout}\n{stderr}"
    if return_code != 0:
        return "failed"
    if any(marker in combined for marker in EXPLICIT_SKIP_MARKERS):
        return "skipped"
    return "passed"


def classify_result(return_code: int, stdout: str, stderr: str) -> str:
    return classify_test_result("", return_code, stdout, stderr)


def run_one_test(layer: str, module: str) -> dict:
    start = time.time()
    command = [sys.executable, "-m", module]
    display_command = f"python -m {module}"
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=900,
            shell=False,
        )
        stdout = redact(completed.stdout)
        stderr = redact(completed.stderr)
        status = classify_test_result(display_command, completed.returncode, stdout, stderr)
        return_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = redact(exc.stdout or "")
        stderr = redact(exc.stderr or "")
        status = "failed"
        return_code = -1
        stderr = f"{stderr}\nTest timed out after {exc.timeout} seconds.".strip()
    except Exception as exc:
        stdout = ""
        stderr = redact(str(exc))
        status = "failed"
        return_code = -1

    return {
        "layer": layer,
        "module": module,
        "command": display_command,
        "status": status,
        "return_code": return_code,
        "duration_seconds": round(time.time() - start, 3),
        "stdout_tail": stdout[-TAIL_CHARS:],
        "stderr_tail": stderr[-TAIL_CHARS:],
    }


def summarize_results(results: list[dict], duration_seconds: float) -> dict:
    layer_breakdown = {}
    for layer in TEST_MATRIX:
        layer_results = [result for result in results if result["layer"] == layer]
        layer_breakdown[layer] = {
            "total": len(layer_results),
            "passed": sum(1 for result in layer_results if result["status"] == "passed"),
            "failed": sum(1 for result in layer_results if result["status"] == "failed"),
            "skipped": sum(1 for result in layer_results if result["status"] == "skipped"),
        }

    failures = [
        {
            "layer": result["layer"],
            "module": result["module"],
            "command": result["command"],
            "return_code": result["return_code"],
            "stdout_tail": result["stdout_tail"],
            "stderr_tail": result["stderr_tail"],
        }
        for result in results
        if result["status"] == "failed"
    ]

    return {
        "total_tests": len(results),
        "passed_tests": sum(1 for result in results if result["status"] == "passed"),
        "failed_tests": sum(1 for result in results if result["status"] == "failed"),
        "skipped_tests": sum(1 for result in results if result["status"] == "skipped"),
        "failures": failures,
        "duration_seconds": round(duration_seconds, 3),
        "layer_breakdown": layer_breakdown,
        "results": results,
    }


def run_layer6_test_matrix() -> dict:
    started = time.time()
    results = []
    for layer, modules in TEST_MATRIX.items():
        for module in modules:
            results.append(run_one_test(layer, module))

    summary = summarize_results(results, time.time() - started)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    print(json.dumps(run_layer6_test_matrix(), indent=2))
