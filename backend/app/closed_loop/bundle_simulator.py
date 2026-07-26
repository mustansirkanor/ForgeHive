import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from backend.app.closed_loop.bundle_to_strategy import (
    derive_simulation_strategy_from_bundle,
    normalize_bundle_for_simulation,
    slugify,
)
from backend.app.energyplus import config as energyplus_config
from backend.app.energyplus.comparator import calculate_percentage_change
from backend.app.energyplus.idf_adapter import apply_action_bundle_to_idf
from backend.app.energyplus.parser import parse_energyplus_run
from backend.app.energyplus.runner import run_energyplus


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LAYER5_RUNS_DIR = PROJECT_ROOT / "runs" / "layer_5"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "layer_5_closed_loop"
CACHE_FILE = ARTIFACT_DIR / "simulation_cache.json"


def load_cache() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}


def save_cache(cache: dict) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def stable_bundle_key(bundle: dict) -> str:
    normalized = normalize_bundle_for_simulation(bundle)
    payload = {
        "bundle": normalized,
        "model": str(energyplus_config.DEFAULT_MODEL),
        "weather": str(energyplus_config.DEFAULT_WEATHER),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def load_baseline_metrics(baseline_metrics: dict | None = None) -> dict:
    if baseline_metrics:
        return {
            "energy_kwh": float(baseline_metrics.get("energy_kwh", baseline_metrics.get("electricity_kwh", 0)) or 0),
            "carbon_kg": float(baseline_metrics.get("carbon_kg", 0) or 0),
        }

    try:
        from backend.app.energyplus.comparison_api import get_baseline_vs_forgehive_comparison

        comparison = get_baseline_vs_forgehive_comparison()
        baseline = comparison.get("baseline", {}) if not comparison.get("error") else {}
        return {
            "energy_kwh": float(baseline.get("energy_kwh", 0) or 0),
            "carbon_kg": float(baseline.get("carbon_kg", 0) or 0),
        }
    except Exception:
        return {"energy_kwh": 0.0, "carbon_kg": 0.0}


def build_result(
    bundle: dict,
    strategy: dict,
    status: str,
    run_dir: str,
    baseline: dict,
    parser_output: dict | None = None,
    notes: list[str] | None = None,
    error: str | None = None,
    idf_adapter_report: dict | None = None,
) -> dict:
    parser_output = parser_output or {}
    metrics = parser_output.get("metrics", {})
    energy_kwh = float(metrics.get("electricity_kwh", 0) or 0)
    carbon_kg = float(metrics.get("carbon_kg", 0) or 0)
    baseline_energy = float(baseline.get("energy_kwh", 0) or 0)
    baseline_carbon = float(baseline.get("carbon_kg", 0) or 0)
    energy_saved = baseline_energy - energy_kwh if status == "success" else 0.0
    carbon_reduced = baseline_carbon - carbon_kg if status == "success" else 0.0

    return {
        "bundle_id": bundle.get("bundle_id", bundle.get("bundle_name", "")),
        "bundle_name": bundle.get("bundle_name", ""),
        "simulation_status": status,
        "run_dir": run_dir,
        "strategy_name": strategy.get("strategy_name", ""),
        "actions_simulated": strategy.get("actions_used", []),
        "energy_kwh": round(energy_kwh, 4),
        "carbon_kg": round(carbon_kg, 4),
        "comfort_violation_minutes": 0,
        "comfort_status": "Safe" if status == "success" else "Unknown",
        "anomaly_count": 0,
        "baseline_energy_kwh": round(baseline_energy, 4),
        "baseline_carbon_kg": round(baseline_carbon, 4),
        "energy_saved_kwh": round(energy_saved, 4),
        "energy_saved_percent": round(calculate_percentage_change(baseline_energy, energy_kwh), 4) if status == "success" else 0.0,
        "carbon_reduced_kg": round(carbon_reduced, 4),
        "carbon_reduced_percent": round(calculate_percentage_change(baseline_carbon, carbon_kg), 4) if status == "success" else 0.0,
        "simulation_notes": notes or [],
        "error": error,
        "raw_parser_output": parser_output,
        "idf_adapter_report": idf_adapter_report or {},
    }


def create_run_paths(bundle: dict) -> tuple[Path, Path]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    slug = slugify(bundle.get("bundle_name", "candidate_bundle"))
    run_dir = LAYER5_RUNS_DIR / f"{timestamp}_{slug}"
    run_dir.mkdir(parents=True, exist_ok=True)
    modified_idf = run_dir / "modified_model.idf"
    return run_dir, modified_idf


def simulate_action_bundle(bundle: dict, baseline_metrics: dict | None = None) -> dict:
    normalized_bundle = normalize_bundle_for_simulation(bundle)
    baseline = load_baseline_metrics(baseline_metrics)
    strategy = derive_simulation_strategy_from_bundle(normalized_bundle)
    notes = list(strategy.get("simulation_notes", []))
    cache_key = stable_bundle_key(normalized_bundle)
    cache = load_cache()

    if os.environ.get("FORCE_LAYER5_RESIMULATE", "").lower() != "true":
        cached = cache.get(cache_key)
        if cached and cached.get("simulation_status") == "success":
            cached_result = dict(cached)
            cached_result.setdefault("simulation_notes", []).append("Reused successful Layer 5 simulation cache.")
            return cached_result

    run_dir, modified_idf = create_run_paths(normalized_bundle)

    try:
        if not energyplus_config.DEFAULT_MODEL.exists():
            raise FileNotFoundError(f"EnergyPlus model not found: {energyplus_config.DEFAULT_MODEL}")
        if not energyplus_config.ENERGYPLUS_EXE.exists():
            raise FileNotFoundError(f"EnergyPlus executable not found: {energyplus_config.ENERGYPLUS_EXE}")

        idf_adapter_report = apply_action_bundle_to_idf(
            str(energyplus_config.DEFAULT_MODEL),
            str(modified_idf),
            normalized_bundle,
            strategy,
        )
        for change in idf_adapter_report.get("change_log", []):
            notes.append(
                f"IDF adapter changed {change.get('object_type')} '{change.get('object_name')}' "
                f"{change.get('field')} from {change.get('old_value')} to {change.get('new_value')}."
            )
        for action in idf_adapter_report.get("actions_metadata_only", []):
            notes.append(f"IDF adapter kept {action.get('action_type')} as metadata-only for this IDF.")
        notes.extend(idf_adapter_report.get("warnings", []))

        runner_result = run_energyplus(
            run_name=f"layer_5/{run_dir.name}",
            model_path=modified_idf,
            weather_path=energyplus_config.DEFAULT_WEATHER,
            clean=True,
        )
        actual_run_dir = runner_result.get("output_dir", str(run_dir))
        parser_output = parse_energyplus_run(actual_run_dir)
        completed = parser_output.get("simulation", {}).get("completed") and not parser_output.get("simulation", {}).get("has_fatal")
        status = "success" if completed else "failed"
        error = None if completed else "EnergyPlus did not complete successfully."
        result = build_result(normalized_bundle, strategy, status, actual_run_dir, baseline, parser_output, notes, error, idf_adapter_report)
        if status == "success":
            cache[cache_key] = result
            save_cache(cache)
        return result
    except Exception as exc:
        if energyplus_config.DEFAULT_MODEL.exists() and not modified_idf.exists():
            try:
                shutil.copy2(energyplus_config.DEFAULT_MODEL, modified_idf)
            except OSError:
                pass
        result = build_result(normalized_bundle, strategy, "failed", str(run_dir), baseline, {}, notes, str(exc), locals().get("idf_adapter_report", {}))
        return result
    finally:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        if not CACHE_FILE.exists():
            save_cache(cache)


def simulate_candidate_bundles(candidate_bundles: list[dict], baseline_metrics: dict | None = None) -> dict:
    baseline = load_baseline_metrics(baseline_metrics)
    simulation_results = []
    notes = []

    for bundle in candidate_bundles or []:
        try:
            simulation_results.append(simulate_action_bundle(bundle, baseline))
        except Exception as exc:
            normalized = normalize_bundle_for_simulation(bundle)
            strategy = derive_simulation_strategy_from_bundle(normalized)
            simulation_results.append(
                build_result(normalized, strategy, "failed", "", baseline, {}, ["Simulation exception captured."], str(exc), {})
            )

    successful_results = [result for result in simulation_results if result.get("simulation_status") == "success"]
    failed_results = [result for result in simulation_results if result.get("simulation_status") != "success"]
    if not successful_results:
        notes.append("No candidate bundles simulated successfully; downstream Layer 5 will choose safe no-action.")

    return {
        "baseline": baseline,
        "simulation_results": simulation_results,
        "successful_results": successful_results,
        "failed_results": failed_results,
        "simulation_count": len(simulation_results),
        "successful_simulation_count": len(successful_results),
        "notes": notes,
    }
