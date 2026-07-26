import csv
from pathlib import Path


JOULES_PER_KWH = 3_600_000
CARBON_KG_PER_KWH = 0.45


def safe_float(value) -> float:
    try:
        if value is None or str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def joules_to_kwh(joules: float) -> float:
    return joules / JOULES_PER_KWH


def read_file_safe(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


def clean_meter_name(column_name: str) -> str:
    return column_name.split("[J]")[0].strip()


def is_run_period_column(column_name: str) -> bool:
    return "[J]" in column_name and "(RunPeriod)" in column_name


def is_monthly_column(column_name: str) -> bool:
    return "[J]" in column_name and "(Monthly)" in column_name


def meter_matches(meter_name: str, keywords: list[str]) -> bool:
    normalized = meter_name.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def parse_meter_csv(path: Path) -> dict:
    if not path.exists():
        return {
            "available": False,
            "message": f"Meter CSV not found: {path}",
            "all_meters_kwh": {},
        }

    try:
        with path.open(newline="", errors="ignore") as meter_file:
            rows = list(csv.DictReader(meter_file))
    except OSError as exc:
        return {
            "available": False,
            "message": f"Could not read meter CSV: {exc}",
            "all_meters_kwh": {},
        }

    if not rows:
        return {
            "available": False,
            "message": f"Meter CSV is empty: {path}",
            "all_meters_kwh": {},
        }

    fieldnames = rows[0].keys()
    all_meters_joules = {}

    for column_name in fieldnames:
        if is_run_period_column(column_name):
            meter_name = clean_meter_name(column_name)
            all_meters_joules[meter_name] = sum(safe_float(row.get(column_name)) for row in rows)

    monthly_totals = {}
    for column_name in fieldnames:
        if is_monthly_column(column_name):
            meter_name = clean_meter_name(column_name)
            monthly_totals[meter_name] = sum(safe_float(row.get(column_name)) for row in rows)

    for meter_name, total_joules in monthly_totals.items():
        if all_meters_joules.get(meter_name, 0.0) == 0.0:
            all_meters_joules[meter_name] = total_joules

    all_meters_kwh = {
        meter_name: joules_to_kwh(total_joules)
        for meter_name, total_joules in sorted(all_meters_joules.items())
    }

    return {
        "available": bool(all_meters_kwh),
        "message": "Meter CSV parsed successfully." if all_meters_kwh else "No Joule meter columns found.",
        "all_meters_kwh": all_meters_kwh,
    }


def get_meter_total(all_meters_kwh: dict, keywords: list[str]) -> float:
    for meter_name, total_kwh in all_meters_kwh.items():
        if meter_matches(meter_name, keywords):
            return total_kwh
    return 0.0


def parse_energyplus_run(run_dir) -> dict:
    run_path = Path(run_dir)
    end_file = run_path / "eplusout.end"
    err_file = run_path / "eplusout.err"
    meter_file = run_path / "eplusmtr.csv"

    end_text = read_file_safe(end_file)
    err_text = read_file_safe(err_file)

    completed = "EnergyPlus Completed Successfully" in end_text
    has_fatal = "Fatal" in err_text
    has_severe = "Severe" in err_text and "0 Severe Errors" not in err_text

    meter_result = parse_meter_csv(meter_file)
    all_meters_kwh = meter_result["all_meters_kwh"]

    electricity_kwh = get_meter_total(all_meters_kwh, ["Electricity:Facility"])
    cooling_kwh = get_meter_total(all_meters_kwh, ["Cooling"])
    heating_kwh = get_meter_total(all_meters_kwh, ["Heating"])
    carbon_kg = electricity_kwh * CARBON_KG_PER_KWH

    messages = []
    if not end_file.exists():
        messages.append(f"End file not found: {end_file}")
    if not err_file.exists():
        messages.append(f"Error file not found: {err_file}")
    if meter_result["message"]:
        messages.append(meter_result["message"])

    return {
        "run_dir": str(run_path),
        "simulation": {
            "completed": completed,
            "has_fatal": has_fatal,
            "has_severe": has_severe,
            "end_summary": end_text.strip(),
        },
        "metrics": {
            "available": meter_result["available"],
            "electricity_kwh": electricity_kwh,
            "cooling_kwh": cooling_kwh,
            "heating_kwh": heating_kwh,
            "carbon_kg": carbon_kg,
            "all_meters_kwh": all_meters_kwh,
        },
        "messages": messages,
    }
