from pathlib import Path

from backend.app.energyplus.idf_adapter import apply_action_bundle_to_idf


def split_value_and_suffix(line: str) -> tuple[str, str]:
    for separator in (",", ";"):
        if separator in line:
            index = line.index(separator)
            return line[:index], line[index:]
    return line, ""


def safe_float(value: str) -> float | None:
    try:
        return float(value.strip())
    except ValueError:
        return None


def replace_numeric_value(line: str, new_value: float) -> str:
    value_part, suffix = split_value_and_suffix(line)
    leading_spaces = value_part[: len(value_part) - len(value_part.lstrip())]
    return f"{leading_spaces}{new_value:.6g}{suffix}"


def get_field_value(line: str) -> str:
    value_part, _ = split_value_and_suffix(line)
    return value_part.strip()


def get_object_name(object_lines: list[str]) -> str:
    if len(object_lines) < 2:
        return "Unnamed object"
    return get_field_value(object_lines[1]) or "Unnamed object"


def reduce_field(
    object_lines: list[str],
    field_index: int,
    object_name: str,
    label: str,
    reduction_percent: float,
) -> tuple[bool, str | None]:
    line_index = field_index + 1
    if line_index >= len(object_lines):
        return False, None

    original_value = safe_float(get_field_value(object_lines[line_index]))
    if original_value is None:
        return False, None

    new_value = max(original_value * (1 - reduction_percent), original_value * 0.5)
    object_lines[line_index] = replace_numeric_value(object_lines[line_index], new_value)

    message = (
        f"Reduced {label} in '{object_name}' by {reduction_percent * 100:.0f}% "
        f"from {original_value:.6g} to {new_value:.6g}."
    )
    return True, message


def modify_lights_object(object_lines: list[str]) -> tuple[list[str], list[str]]:
    changes = []
    object_name = get_object_name(object_lines)
    calculation_method = get_field_value(object_lines[4]).lower() if len(object_lines) > 4 else ""

    if calculation_method == "lightinglevel":
        changed, message = reduce_field(
            object_lines,
            field_index=4,
            object_name=object_name,
            label="lighting level",
            reduction_percent=0.10,
        )
    elif calculation_method == "watts/area":
        changed, message = reduce_field(
            object_lines,
            field_index=5,
            object_name=object_name,
            label="lighting watts per floor area",
            reduction_percent=0.10,
        )
    else:
        changed, message = False, None

    if changed and message:
        changes.append(message)

    return object_lines, changes


def modify_electric_equipment_object(object_lines: list[str]) -> tuple[list[str], list[str]]:
    changes = []
    object_name = get_object_name(object_lines)
    calculation_method = get_field_value(object_lines[4]).lower() if len(object_lines) > 4 else ""

    if calculation_method == "equipmentlevel":
        changed, message = reduce_field(
            object_lines,
            field_index=4,
            object_name=object_name,
            label="electric equipment design level",
            reduction_percent=0.05,
        )
    elif calculation_method == "watts/area":
        changed, message = reduce_field(
            object_lines,
            field_index=5,
            object_name=object_name,
            label="electric equipment watts per floor area",
            reduction_percent=0.05,
        )
    else:
        changed, message = False, None

    if changed and message:
        changes.append(message)

    return object_lines, changes


def read_idf_object(lines: list[str], start_index: int) -> tuple[list[str], int]:
    object_lines = []
    index = start_index

    while index < len(lines):
        object_lines.append(lines[index])
        if ";" in lines[index]:
            break
        index += 1

    return object_lines, index + 1


def apply_eco_strategy(source_idf: Path, output_idf: Path) -> dict:
    source_path = Path(source_idf)
    output_path = Path(output_idf)

    result = {
        "strategy_name": "eco_mode",
        "source_idf": str(source_path),
        "output_idf": str(output_path),
        "changes_applied": [],
        "warnings": [],
    }

    if not source_path.exists():
        raise FileNotFoundError(f"Source IDF not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    adapter_report = apply_action_bundle_to_idf(
        str(source_path),
        str(output_path),
        {
            "bundle_name": "legacy_eco_strategy",
            "actions": [
                {
                    "action_type": "lighting_adjustment",
                    "target": "unoccupied_zones",
                    "description": "Legacy eco strategy lighting reduction.",
                    "parameters": {"lighting_level_percent": 90},
                }
            ],
        },
        {"strategy_name": "eco_mode", "lighting_level_percent": 90},
    )
    if adapter_report.get("lighting_applied"):
        result["changes_applied"].extend(
            [
                (
                    f"Changed {change['object_type']} '{change['object_name']}' {change['field']} "
                    f"from {change['old_value']} to {change['new_value']}."
                )
                for change in adapter_report.get("change_log", [])
            ]
        )
        result["warnings"].extend(adapter_report.get("warnings", []))
        result["idf_adapter_report"] = adapter_report
        return result

    lines = source_path.read_text(errors="ignore").splitlines(keepends=True)
    modified_lines = []
    index = 0

    while index < len(lines):
        stripped = lines[index].strip().lower()

        if stripped == "lights,":
            object_lines, index = read_idf_object(lines, index)
            object_lines, changes = modify_lights_object(object_lines)
            result["changes_applied"].extend(changes)
            modified_lines.extend(object_lines)
            continue

        if stripped == "electricequipment,":
            object_lines, index = read_idf_object(lines, index)
            object_lines, changes = modify_electric_equipment_object(object_lines)
            result["changes_applied"].extend(changes)
            modified_lines.extend(object_lines)
            continue

        modified_lines.append(lines[index])
        index += 1

    if not result["changes_applied"]:
        result["warnings"].append("No Lights or ElectricEquipment objects could be safely modified.")

    output_path.write_text("".join(modified_lines))
    return result
