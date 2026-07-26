import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from backend.app.closed_loop.bundle_simulator import load_baseline_metrics
from backend.app.closed_loop.bundle_to_strategy import (
    derive_simulation_strategy_from_bundle,
    normalize_bundle_for_simulation,
    slugify,
)
from backend.app.energyplus import config as energyplus_config
from backend.app.energyplus.comparator import calculate_percentage_change
from backend.app.energyplus.idf_adapter import apply_action_bundle_to_idf
from backend.app.energyplus.parser import parse_energyplus_run


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXECUTIONS_DIR = PROJECT_ROOT / "runs" / "layer_5" / "executions"
DIGITAL_TWIN_NOTE = "This execution was applied only inside the EnergyPlus digital twin."


def build_execution_bundle_from_safety_approval(plan: dict) -> dict:
    approval = plan.get("final_safety_approval") or {}
    selected = plan.get("selected_bundle") or {}
    original = selected.get("original_bundle") or {}
    approved_actions = list(approval.get("approved_actions") or [])

    bundle = normalize_bundle_for_simulation(original)
    bundle["bundle_id"] = approval.get("selected_bundle_id") or bundle.get("bundle_id")
    bundle["bundle_name"] = approval.get("selected_bundle_name") or bundle.get("bundle_name")
    bundle["actions"] = approved_actions
    bundle["safety_summary"] = approval.get("safety_summary", "")
    bundle["blocked_actions_not_executed"] = approval.get("blocked_actions", [])
    bundle["execution_scope"] = "energyplus_digital_twin_only"
    return bundle


def blocked_execution_result(plan: dict, reason: str) -> dict:
    approval = plan.get("final_safety_approval") or {}
    baseline = load_baseline_metrics(plan.get("baseline"))
    return {
        "phase": "5.4",
        "execution_status": "blocked",
        "execution_applied": False,
        "execution_scope": "energyplus_digital_twin_only",
        "selected_bundle_id": approval.get("selected_bundle_id"),
        "selected_bundle_name": approval.get("selected_bundle_name"),
        "approved_actions_executed": [],
        "blocked_actions_not_executed": approval.get("blocked_actions", []),
        "run_dir": "",
        "strategy_name": "",
        "baseline_energy_kwh": round(float(baseline.get("energy_kwh", 0) or 0), 4),
        "baseline_carbon_kg": round(float(baseline.get("carbon_kg", 0) or 0), 4),
        "executed_energy_kwh": 0.0,
        "executed_carbon_kg": 0.0,
        "energy_saved_kwh": 0.0,
        "energy_saved_percent": 0.0,
        "carbon_reduced_kg": 0.0,
        "carbon_reduced_percent": 0.0,
        "comfort_violation_minutes": 0.0,
        "comfort_status": "Unknown",
        "anomaly_count": 0,
        "parser_output": {},
        "idf_adapter_report": {},
        "execution_notes": [reason, DIGITAL_TWIN_NOTE, "No EnergyPlus execution was started."],
        "error": None,
    }


def failed_execution_result(bundle: dict, strategy: dict, run_dir: Path, baseline: dict, notes: list[str], error: str) -> dict:
    return {
        "phase": "5.4",
        "execution_status": "failed",
        "execution_applied": False,
        "execution_scope": "energyplus_digital_twin_only",
        "selected_bundle_id": bundle.get("bundle_id"),
        "selected_bundle_name": bundle.get("bundle_name"),
        "approved_actions_executed": bundle.get("actions", []),
        "blocked_actions_not_executed": bundle.get("blocked_actions_not_executed", []),
        "run_dir": str(run_dir),
        "strategy_name": strategy.get("strategy_name", ""),
        "baseline_energy_kwh": round(float(baseline.get("energy_kwh", 0) or 0), 4),
        "baseline_carbon_kg": round(float(baseline.get("carbon_kg", 0) or 0), 4),
        "executed_energy_kwh": 0.0,
        "executed_carbon_kg": 0.0,
        "energy_saved_kwh": 0.0,
        "energy_saved_percent": 0.0,
        "carbon_reduced_kg": 0.0,
        "carbon_reduced_percent": 0.0,
        "comfort_violation_minutes": 0.0,
        "comfort_status": "Unknown",
        "anomaly_count": 0,
        "parser_output": {},
        "idf_adapter_report": strategy.get("idf_adapter_report", {}),
        "execution_notes": notes + [DIGITAL_TWIN_NOTE],
        "error": error,
    }


def create_execution_paths(bundle: dict) -> tuple[Path, Path]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    run_dir = EXECUTIONS_DIR / f"{timestamp}_{slugify(bundle.get('bundle_name', 'approved_bundle'))}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, run_dir / "modified_model.idf"


def run_energyplus_in_execution_dir(model_path: Path, run_dir: Path) -> dict:
    command = [
        str(energyplus_config.ENERGYPLUS_EXE),
        "-w",
        str(energyplus_config.DEFAULT_WEATHER),
        "-d",
        str(run_dir),
        "-r",
        str(model_path),
    ]
    process = subprocess.run(command, capture_output=True, text=True, shell=False)
    return {
        "return_code": process.returncode,
        "stdout_tail": process.stdout[-1000:],
        "stderr_tail": process.stderr[-1000:],
    }


def build_executed_result(bundle: dict, strategy: dict, run_dir: Path, baseline: dict, parser_output: dict, notes: list[str]) -> dict:
    metrics = parser_output.get("metrics", {})
    executed_energy = float(metrics.get("electricity_kwh", 0) or 0)
    executed_carbon = float(metrics.get("carbon_kg", 0) or 0)
    baseline_energy = float(baseline.get("energy_kwh", 0) or 0)
    baseline_carbon = float(baseline.get("carbon_kg", 0) or 0)
    energy_saved = baseline_energy - executed_energy
    carbon_reduced = baseline_carbon - executed_carbon

    return {
        "phase": "5.4",
        "execution_status": "executed",
        "execution_applied": True,
        "execution_scope": "energyplus_digital_twin_only",
        "selected_bundle_id": bundle.get("bundle_id"),
        "selected_bundle_name": bundle.get("bundle_name"),
        "approved_actions_executed": bundle.get("actions", []),
        "blocked_actions_not_executed": bundle.get("blocked_actions_not_executed", []),
        "run_dir": str(run_dir),
        "strategy_name": strategy.get("strategy_name", ""),
        "baseline_energy_kwh": round(baseline_energy, 4),
        "baseline_carbon_kg": round(baseline_carbon, 4),
        "executed_energy_kwh": round(executed_energy, 4),
        "executed_carbon_kg": round(executed_carbon, 4),
        "energy_saved_kwh": round(energy_saved, 4),
        "energy_saved_percent": round(calculate_percentage_change(baseline_energy, executed_energy), 4),
        "carbon_reduced_kg": round(carbon_reduced, 4),
        "carbon_reduced_percent": round(calculate_percentage_change(baseline_carbon, executed_carbon), 4),
        "comfort_violation_minutes": 0.0,
        "comfort_status": "Safe",
        "anomaly_count": 0,
        "parser_output": parser_output,
        "idf_adapter_report": strategy.get("idf_adapter_report", {}),
        "execution_notes": notes + [DIGITAL_TWIN_NOTE],
        "error": None,
    }


def execute_approved_bundle_in_digital_twin(plan_5_1_3: dict) -> dict:
    approval = plan_5_1_3.get("final_safety_approval") or {}
    if not approval.get("execution_ready"):
        return blocked_execution_result(
            plan_5_1_3,
            approval.get("safety_summary", "Final Safety Governor did not approve execution."),
        )

    bundle = build_execution_bundle_from_safety_approval(plan_5_1_3)
    if not bundle.get("actions"):
        return blocked_execution_result(plan_5_1_3, "No approved actions were available for digital twin execution.")

    baseline = load_baseline_metrics(plan_5_1_3.get("baseline"))
    strategy = derive_simulation_strategy_from_bundle(bundle)
    notes = list(strategy.get("simulation_notes", []))
    run_dir, modified_idf = create_execution_paths(bundle)

    try:
        if not energyplus_config.DEFAULT_MODEL.exists():
            raise FileNotFoundError(f"EnergyPlus model not found: {energyplus_config.DEFAULT_MODEL}")
        if not energyplus_config.DEFAULT_WEATHER.exists():
            raise FileNotFoundError(f"Weather file not found: {energyplus_config.DEFAULT_WEATHER}")
        if not energyplus_config.ENERGYPLUS_EXE.exists():
            raise FileNotFoundError(f"EnergyPlus executable not found: {energyplus_config.ENERGYPLUS_EXE}")

        idf_adapter_report = apply_action_bundle_to_idf(
            str(energyplus_config.DEFAULT_MODEL),
            str(modified_idf),
            bundle,
            strategy,
        )
        strategy["idf_adapter_report"] = idf_adapter_report
        for change in idf_adapter_report.get("change_log", []):
            notes.append(
                f"IDF adapter changed {change.get('object_type')} '{change.get('object_name')}' "
                f"{change.get('field')} from {change.get('old_value')} to {change.get('new_value')}."
            )
        for action in idf_adapter_report.get("actions_metadata_only", []):
            notes.append(f"IDF adapter kept {action.get('action_type')} as metadata-only for this IDF.")
        notes.extend(idf_adapter_report.get("warnings", []))
        notes.append("Approved Layer 5 actions were translated by the Phase 5.7 IDF adapter where safe objects were found.")

        runner_result = run_energyplus_in_execution_dir(modified_idf, run_dir)
        notes.append(f"EnergyPlus return_code={runner_result.get('return_code')}.")
        parser_output = parse_energyplus_run(run_dir)
        completed = parser_output.get("simulation", {}).get("completed") and not parser_output.get("simulation", {}).get("has_fatal")
        if not completed:
            return failed_execution_result(
                bundle,
                strategy,
                run_dir,
                baseline,
                notes,
                "EnergyPlus did not complete successfully.",
            )
        return build_executed_result(bundle, strategy, run_dir, baseline, parser_output, notes)
    except Exception as exc:
        if energyplus_config.DEFAULT_MODEL.exists() and not modified_idf.exists():
            try:
                shutil.copy2(energyplus_config.DEFAULT_MODEL, modified_idf)
            except OSError:
                pass
        return failed_execution_result(bundle, strategy, run_dir, baseline, notes, str(exc))
    finally:
        marker = run_dir / "layer5_execution_metadata.json"
        if run_dir.exists() and not marker.exists():
            marker.write_text(json.dumps({"scope": "energyplus_digital_twin_only", "note": DIGITAL_TWIN_NOTE}, indent=2))
