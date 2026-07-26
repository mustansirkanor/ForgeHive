import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "final_submission"
OUTPUT_FILE = OUTPUT_DIR / "forgehive_artifact_audit.json"


REQUIRED_ARTIFACTS = {
    "Layer 1": [
        "artifacts/layer_1_proof/layer1_proof.json",
        "artifacts/layer_1_proof/dashboard_metrics.json",
        "artifacts/layer_1_proof/layer1_summary.md",
    ],
    "Layer 2": [
        "artifacts/layer_2_intelligence/building_intelligence_package.json",
        "artifacts/layer_2_intelligence/dashboard_intelligence.json",
    ],
    "Layer 3": [
        "artifacts/layer_3_decision/layer3_proof_package.json",
        "artifacts/layer_3_decision/layer3_dashboard_summary.json",
        "artifacts/layer_3_decision/layer3_summary.md",
    ],
    "Layer 4": [
        "artifacts/layer_4_cognitive/layer4_operator_demo.json",
        "artifacts/layer_4_cognitive/layer4_dashboard_summary.json",
        "artifacts/layer_4_cognitive/layer4_summary.md",
    ],
    "Layer 5": [
        "artifacts/layer_5_closed_loop/layer5_phase_1_3_proof.json",
        "artifacts/layer_5_closed_loop/layer5_dashboard_summary.json",
        "artifacts/layer_5_closed_loop/layer5_full_closed_loop_proof.json",
        "artifacts/layer_5_closed_loop/layer5_execution_result.json",
        "artifacts/layer_5_closed_loop/layer5_learning_report.json",
        "artifacts/layer_5_closed_loop/layer5_dashboard_final.json",
        "artifacts/layer_5_closed_loop/layer5_7_real_ollama_full_loop.json",
        "artifacts/layer_5_closed_loop/layer5_7_idf_adapter_report.json",
        "artifacts/layer_5_closed_loop/layer5_7_dashboard_summary.json",
        "artifacts/layer_5_closed_loop/layer5_7_summary.md",
    ],
    "Layer 8": [
        "artifacts/layer_8_experience_graph/experience_graph_summary.json",
        "artifacts/layer_8_experience_graph/experience_retrieval_demo.json",
        "artifacts/layer_8_experience_graph/experience_learning_demo.json",
        "artifacts/layer_8_experience_graph/layer8_summary.md",
    ],
}


def redact_secrets(value):
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if isinstance(value, str):
        return value.replace(api_key, "[REDACTED_OPENROUTER_API_KEY]") if api_key else value
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_secrets(item) for key, item in value.items()}
    return value


def load_json(path: Path) -> tuple[dict | list | None, str | None]:
    try:
        return json.loads(path.read_text(errors="ignore")), None
    except Exception as exc:
        return None, str(exc)


def get_nested(data: dict, path: list[str], default=None):
    current = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def check_flags(relative_path: str, data) -> list[str]:
    warnings = []
    if not isinstance(data, dict):
        return warnings

    if "layer5_7_dashboard_summary.json" in relative_path:
        expected = {
            "realBuildingExecution": False,
            "digitalTwinExecution": True,
            "safetyGovernorUsed": True,
            "rlBanditUsed": True,
            "knowledgeGraphUsed": True,
            "judgeReady": True,
        }
        for key, value in expected.items():
            if data.get(key) is not value:
                warnings.append(f"{relative_path}: expected {key}={value}, got {data.get(key)}.")

    if "layer5_dashboard_final.json" in relative_path:
        expected = {
            "realBuildingExecutionEnabled": False,
            "safetyGovernorUsed": True,
            "rlBanditUsed": True,
            "knowledgeGraphUsed": True,
        }
        for key, value in expected.items():
            if data.get(key) is not value:
                warnings.append(f"{relative_path}: expected {key}={value}, got {data.get(key)}.")

    if "layer5_7_real_ollama_full_loop.json" in relative_path:
        if data.get("real_building_execution") is not False:
            warnings.append(f"{relative_path}: real_building_execution must be false.")
        if data.get("digital_twin_execution") is not True:
            warnings.append(f"{relative_path}: digital_twin_execution should be true for final demo.")
        if data.get("selected_provider") not in {"ollama", "openrouter"}:
            warnings.append(f"{relative_path}: final demo provider should be ollama or openrouter.")

    if "layer5_full_closed_loop_proof.json" in relative_path:
        if data.get("real_building_execution") is not False:
            warnings.append(f"{relative_path}: real_building_execution must be false.")
        dashboard = data.get("phase_5_6_dashboard", {})
        if dashboard and dashboard.get("realBuildingExecutionEnabled") is not False:
            warnings.append(f"{relative_path}: dashboard realBuildingExecutionEnabled must be false.")

    return warnings


def run_artifact_audit() -> dict:
    missing_files = []
    invalid_json_files = []
    warnings = []
    json_files_checked = 0
    existing_files = 0
    layer_breakdown = {}

    for layer, relative_paths in REQUIRED_ARTIFACTS.items():
        layer_existing = 0
        for relative_path in relative_paths:
            path = PROJECT_ROOT / relative_path
            if not path.exists():
                missing_files.append(relative_path)
                continue

            existing_files += 1
            layer_existing += 1
            if path.suffix.lower() == ".json":
                json_files_checked += 1
                data, error = load_json(path)
                if error:
                    invalid_json_files.append({"file": relative_path, "error": error})
                else:
                    warnings.extend(check_flags(relative_path, redact_secrets(data)))

        layer_breakdown[layer] = {
            "required": len(relative_paths),
            "existing": layer_existing,
            "missing": len(relative_paths) - layer_existing,
        }

    audit = {
        "required_file_count": sum(len(paths) for paths in REQUIRED_ARTIFACTS.values()),
        "existing_file_count": existing_files,
        "json_files_checked": json_files_checked,
        "missing_files": missing_files,
        "invalid_json_files": invalid_json_files,
        "warnings": warnings,
        "layer_breakdown": layer_breakdown,
        "audit_passed": not missing_files and not invalid_json_files and not warnings,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(audit, indent=2))
    return audit


if __name__ == "__main__":
    print(json.dumps(run_artifact_audit(), indent=2))
