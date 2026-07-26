import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from backend.app.energyplus.config import (
    ENERGYPLUS_EXE,
    DEFAULT_MODEL,
    DEFAULT_WEATHER,
    RUNS_DIR,
)


def validate_paths(model_path: Path, weather_path: Path) -> None:
    if not ENERGYPLUS_EXE.exists():
        raise FileNotFoundError(f"EnergyPlus executable not found: {ENERGYPLUS_EXE}")

    if not model_path.exists():
        raise FileNotFoundError(f"EnergyPlus model not found: {model_path}")

    if not weather_path.exists():
        raise FileNotFoundError(f"Weather file not found: {weather_path}")


def read_file_safe(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


def run_energyplus(
    run_name: str = "python_baseline",
    model_path: Path = DEFAULT_MODEL,
    weather_path: Path = DEFAULT_WEATHER,
    clean: bool = True,
) -> dict:
    validate_paths(model_path, weather_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = RUNS_DIR / f"{run_name}_{timestamp}"

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        str(ENERGYPLUS_EXE),
        "-w",
        str(weather_path),
        "-d",
        str(output_dir),
        "-r",
        str(model_path),
    ]

    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        shell=False,
    )

    end_file = output_dir / "eplusout.end"
    err_file = output_dir / "eplusout.err"

    end_text = read_file_safe(end_file)
    err_text = read_file_safe(err_file)

    completed = "EnergyPlus Completed Successfully" in end_text
    has_fatal = "Fatal" in err_text
    has_severe = "Severe" in err_text and "0 Severe Errors" not in err_text

    return {
        "run_name": run_name,
        "output_dir": str(output_dir),
        "return_code": process.returncode,
        "completed": completed,
        "has_fatal": has_fatal,
        "has_severe": has_severe,
        "end_summary": end_text.strip(),
        "stdout_tail": process.stdout[-1000:],
        "stderr_tail": process.stderr[-1000:],
        "important_files": {
            "end": str(end_file),
            "err": str(err_file),
            "table": str(output_dir / "eplustbl.htm"),
            "meter_csv": str(output_dir / "eplusmtr.csv"),
        },
    }
