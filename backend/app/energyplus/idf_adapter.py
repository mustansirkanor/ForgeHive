import json
import re
import shutil
from pathlib import Path


IDF_ADAPTER_VERSION = "5.7"


def parse_float_safe(value: str) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def safe_float(value) -> float | None:
    return parse_float_safe(value)


def clamp(value, minimum: float, maximum: float, default: float) -> float:
    numeric = safe_float(value)
    if numeric is None:
        numeric = default
    return max(minimum, min(maximum, numeric))


def strip_inline_comment(value: str) -> str:
    return str(value).split("!", 1)[0].strip()


def split_comment(line: str) -> tuple[str, str]:
    if "!" not in line:
        return line, ""
    index = line.index("!")
    return line[:index], line[index:]


def split_value_suffix(line: str) -> tuple[str, str, str, str]:
    code, comment = split_comment(line)
    for separator in (",", ";"):
        if separator in code:
            index = code.index(separator)
            value_part = code[:index]
            suffix = code[index:]
            leading = value_part[: len(value_part) - len(value_part.lstrip())]
            return leading, value_part.strip(), suffix, comment
    leading = code[: len(code) - len(code.lstrip())]
    return leading, code.strip(), "", comment


def replace_numeric_field_preserving_comment(line: str, new_value: float) -> str:
    leading, _old_value, suffix, comment = split_value_suffix(line)
    newline = "\n" if line.endswith("\n") else ""
    clean_comment = comment.rstrip("\n")
    return f"{leading}{new_value:.6g}{suffix}{clean_comment}{newline}"


def replace_line_value(line: str, new_value: float) -> str:
    return replace_numeric_field_preserving_comment(line, new_value)


def field_value(line: str) -> str:
    _leading, value, _suffix, _comment = split_value_suffix(line)
    return value


def numeric_field(line: str) -> float | None:
    return safe_float(field_value(line))


def schedule_value_number(line: str) -> float | None:
    code, _comment = split_comment(line)
    if "until:" not in code.lower():
        return None
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", code)
    if not matches:
        return None
    return safe_float(matches[-1])


def replace_schedule_value(line: str, new_value: float) -> str:
    code, comment = split_comment(line)
    newline = "\n" if line.endswith("\n") else ""
    clean_comment = comment.rstrip("\n")
    matches = list(re.finditer(r"[-+]?\d+(?:\.\d+)?", code))
    if not matches:
        return line
    match = matches[-1]
    new_code = f"{code[:match.start()]}{new_value:.6g}{code[match.end():]}"
    return f"{new_code}{clean_comment}{newline}"


def object_header_index(block: list[str]) -> int | None:
    for index, line in enumerate(block):
        value = field_value(line).rstrip(",;").strip()
        if value and not value.startswith("!"):
            return index
    return None


def object_type(block: list[str]) -> str:
    header_index = object_header_index(block)
    if header_index is None:
        return ""
    return field_value(block[header_index]).rstrip(",;").strip()


def object_name(block: list[str]) -> str:
    header_index = object_header_index(block)
    if header_index is None or header_index + 1 >= len(block):
        return "Unnamed object"
    return field_value(block[header_index + 1]) or "Unnamed object"


def object_search_text(block: list[str]) -> str:
    return " ".join(field_value(line).lower() for line in block)


def block_line_index_for_field(block: list[str], field_index: int) -> int | None:
    header_index = object_header_index(block)
    if header_index is None:
        return None
    line_index = header_index + field_index
    return line_index if line_index < len(block) else None


def split_idf_objects(text: str) -> list[dict]:
    objects = []
    current = []
    for line in text.splitlines(keepends=True):
        current.append(line)
        code, _comment = split_comment(line)
        if ";" in code:
            objects.append(
                {
                    "object_type": object_type(current),
                    "object_name": object_name(current),
                    "lines": current,
                }
            )
            current = []
    if current:
        objects.append(
            {
                "object_type": object_type(current),
                "object_name": object_name(current),
                "lines": current,
            }
        )
    return objects


def render_idf_objects(objects: list[dict]) -> str:
    return "".join(line for obj in objects for line in obj.get("lines", []))


def read_idf_blocks(lines: list[str]) -> list[list[str]]:
    return [obj["lines"] for obj in split_idf_objects("".join(lines))]


def write_blocks(path: Path, blocks: list[list[str]]) -> None:
    path.write_text("".join(line for block in blocks for line in block))


def read_percent(parameters: dict, keys: list[str], default: float) -> float:
    for key in keys:
        if key in parameters:
            return clamp(parameters[key], 10, 100, default)
    return default


def lighting_percent(action: dict, strategy: dict | None) -> float:
    parameters = action.get("parameters") if isinstance(action.get("parameters"), dict) else {}
    if "reduction_percent" in parameters:
        reduction = clamp(parameters.get("reduction_percent"), 0, 90, 0)
        return clamp(100 - reduction, 10, 100, 90)
    for key in ("lighting_level_percent", "brightness", "value"):
        if key in parameters:
            return clamp(parameters[key], 10, 100, 35)
    if strategy and "lighting_level_percent" in strategy:
        return clamp(strategy["lighting_level_percent"], 10, 100, 35)
    return 35


def target_includes_occupied(action: dict) -> bool:
    target = str(action.get("target", "")).lower()
    params = action.get("parameters") if isinstance(action.get("parameters"), dict) else {}
    return bool(params.get("applies_to_occupied_zones")) or ("occupied" in target and "unoccupied" not in target)


def append_change(
    report: dict,
    object_type_value: str,
    object_name_value: str,
    field: str,
    old_value: float,
    new_value: float,
    action_type: str,
    extra: dict | None = None,
) -> None:
    change = {
        "object_type": object_type_value,
        "object_name": object_name_value,
        "field": field,
        "old_value": round(float(old_value), 6),
        "new_value": round(float(new_value), 6),
        "action_type": action_type,
    }
    if extra:
        change.update(extra)
    report["change_log"].append(change)


def apply_lighting_action(blocks: list[list[str]], action: dict, strategy: dict | None, report: dict) -> bool:
    percent = lighting_percent(action, strategy)
    if target_includes_occupied(action):
        percent = max(percent, 50)
    factor = percent / 100.0
    changed = False

    for block in blocks:
        if object_type(block).lower() != "lights":
            continue
        name = object_name(block)
        method_index = block_line_index_for_field(block, 4)
        method = field_value(block[method_index]).lower() if method_index is not None else ""
        candidate_indexes = []
        if method == "lightinglevel":
            candidate_indexes.append(block_line_index_for_field(block, 5))
        elif method == "watts/area":
            candidate_indexes.append(block_line_index_for_field(block, 6))
        else:
            header_index = object_header_index(block) or 0
            candidate_indexes.extend(range(header_index + 2, len(block)))

        for index in candidate_indexes:
            if index is None or index >= len(block):
                continue
            old_value = numeric_field(block[index])
            if old_value is None or old_value <= 0:
                continue
            new_value = old_value * factor
            block[index] = replace_line_value(block[index], new_value)
            append_change(report, "Lights", name, f"field_{index}", old_value, new_value, "lighting_adjustment")
            changed = True
            break

    return changed


def schedule_is_hvac(block: list[str]) -> bool:
    text = object_search_text(block)
    name = object_name(block).lower()
    if any(word in text for word in ("occupancy", "people", "light", "equipment", "availability", "avail", "outdoor air", "outside air", "ventilation", " vent")):
        return False
    if name.startswith("oa ") or " oa " in name or name.endswith(" oa") or name.startswith("outdoor air") or name.startswith("outside air"):
        return False
    return any(word in text for word in ("cool", "clg", "heat", "htg", "setpoint", "thermostat", "temperature"))


def block_is_hvac(block: list[str]) -> bool:
    obj = object_type(block).lower()
    text = object_search_text(block)
    if obj in {"thermostatsetpoint:dualsetpoint", "zonecontrol:thermostat"}:
        return True
    if obj in {"schedule:compact", "schedule:constant", "schedule:ruleset"}:
        return schedule_is_hvac(block)
    return any(word in text for word in ("cooling setpoint", "heating setpoint", "thermostat setpoint"))


def hvac_targets(action: dict, strategy: dict | None) -> tuple[float | None, float | None]:
    params = action.get("parameters") if isinstance(action.get("parameters"), dict) else {}
    occupied = target_includes_occupied(action)
    cooling_raw = params.get("cooling_setpoint_c", params.get("setpoint_c", params.get("value")))
    heating_raw = params.get("heating_setpoint_c")
    if cooling_raw is None and strategy:
        cooling_raw = strategy.get("cooling_setpoint_c")
    if heating_raw is None and strategy:
        heating_raw = strategy.get("heating_setpoint_c")
    cooling = None if cooling_raw is None else clamp(cooling_raw, 23 if occupied else 21, 26 if occupied else 30, 26 if occupied else 28)
    heating = None if heating_raw is None else clamp(heating_raw, 16, 24, 20)
    return cooling, heating


def apply_hvac_action(blocks: list[list[str]], action: dict, strategy: dict | None, report: dict) -> bool:
    cooling_target, heating_target = hvac_targets(action, strategy)
    changed = False
    if cooling_target is None and heating_target is None:
        report["warnings"].append("HVAC setpoint action did not include a usable setpoint value.")
        return False

    for block in blocks:
        if not block_is_hvac(block):
            continue
        obj = object_type(block)
        obj_lower = obj.lower()
        name = object_name(block)
        text = object_search_text(block)
        for index in range(2, len(block)):
            old_value = numeric_field(block[index])
            is_compact_schedule_value = False
            if old_value is None and obj_lower == "schedule:compact":
                old_value = schedule_value_number(block[index])
                is_compact_schedule_value = old_value is not None
            if old_value is None:
                continue
            new_value = None
            if cooling_target is not None and 20 <= old_value <= 35 and ("cool" in text or "clg" in text or "thermostat" in text or "setpoint" in text):
                new_value = cooling_target
            elif heating_target is not None and 10 <= old_value <= 24 and ("heat" in text or "htg" in text or "thermostat" in text or "setpoint" in text):
                new_value = heating_target
            if new_value is None or abs(new_value - old_value) < 0.000001:
                continue
            block[index] = replace_schedule_value(block[index], new_value) if is_compact_schedule_value else replace_line_value(block[index], new_value)
            append_change(report, obj, name, f"field_{index}", old_value, new_value, "hvac_setpoint_adjustment")
            changed = True
    return changed


def ventilation_factor(action: dict, strategy: dict | None) -> float:
    params = action.get("parameters") if isinstance(action.get("parameters"), dict) else {}
    if "ventilation_multiplier" in params:
        return clamp(params["ventilation_multiplier"], 0.3, 1.5, 1.0)
    for key in ("ventilation_percent", "outdoor_air_percent", "value"):
        if key in params:
            return clamp(params[key], 30, 100, 40) / 100.0
    if strategy and "ventilation_multiplier" in strategy:
        return clamp(strategy["ventilation_multiplier"], 0.3, 1.5, 1.0)
    if strategy and "ventilation_percent" in strategy:
        return clamp(strategy["ventilation_percent"], 30, 100, 40) / 100.0
    return 0.4


VENTILATION_SCHEDULE_ALLOW_TERMS = (
    "min oa",
    "minimum outdoor air",
    "outdoor air flow",
    "outside air flow",
    "ventilation flow",
    "ventilation fraction",
)

VENTILATION_SCHEDULE_DENY_TERMS = (
    "temp",
    "temperature",
    "supply air temp",
    "heating supply air",
    "cooling supply air",
    "setpoint",
    "thermostat",
    "clg",
    "htg",
)


def ventilation_schedule_is_safe(block: list[str]) -> bool:
    name = object_name(block).lower()
    if any(term in name for term in VENTILATION_SCHEDULE_DENY_TERMS):
        return False
    return any(term in name for term in VENTILATION_SCHEDULE_ALLOW_TERMS)


def block_is_ventilation(block: list[str]) -> bool:
    obj = object_type(block).lower()
    if obj in {"designspecification:outdoorair", "zoneventilation:designflowrate"}:
        return True
    if obj in {"schedule:compact", "schedule:constant", "schedule:ruleset"}:
        return ventilation_schedule_is_safe(block)
    return False


def apply_ventilation_action(blocks: list[list[str]], action: dict, strategy: dict | None, report: dict) -> bool:
    factor = ventilation_factor(action, strategy)
    if target_includes_occupied(action) and factor < 0.5:
        factor = 0.5
    changed = False
    controller_warning_added = False

    for block in blocks:
        obj = object_type(block)
        obj_lower = obj.lower()
        if obj_lower == "controller:outdoorair":
            if not controller_warning_added:
                report["warnings"].append("Controller:OutdoorAir detected but skipped because field-safe editing is not implemented.")
                controller_warning_added = True
            continue
        if obj_lower != "designspecification:outdoorair":
            continue
        name = object_name(block)
        # Only the four numeric outdoor-air design fields are safe to scale.
        for field_index in (3, 4, 5, 6):
            index = block_line_index_for_field(block, field_index)
            if index is None:
                continue
            old_value = numeric_field(block[index])
            if old_value is None or old_value <= 0:
                continue
            new_value = max(old_value * factor, 0.000001)
            if factor < 1 and new_value > old_value:
                new_value = old_value
            if abs(new_value - old_value) < 0.000001:
                continue
            block[index] = replace_line_value(block[index], new_value)
            append_change(report, obj, name, f"field_{field_index}", old_value, new_value, "ventilation_adjustment", {"multiplier": round(factor, 6)})
            changed = True
    return changed


def action_type_has_changes(report: dict, action_type: str) -> bool:
    return any(change.get("action_type") == action_type for change in report.get("change_log", []))


def apply_action_bundle_to_idf(
    source_idf_path: str,
    target_idf_path: str,
    bundle: dict,
    strategy: dict | None = None,
) -> dict:
    source_path = Path(source_idf_path)
    target_path = Path(target_idf_path)
    actions = list((bundle or {}).get("actions") or [])
    report = {
        "source_idf_path": str(source_path),
        "target_idf_path": str(target_path),
        "idf_adapter_version": IDF_ADAPTER_VERSION,
        "actions_requested": actions,
        "actions_applied": [],
        "actions_metadata_only": [],
        "actions_failed": [],
        "lighting_applied": False,
        "hvac_setpoint_applied": False,
        "ventilation_applied": False,
        "change_log": [],
        "warnings": [],
        "success": False,
    }

    if not source_path.exists():
        report["actions_failed"] = actions
        report["warnings"].append(f"Source IDF not found: {source_path}")
        return report

    target_path.parent.mkdir(parents=True, exist_ok=True)
    lines = source_path.read_text(errors="ignore").splitlines(keepends=True)
    blocks = read_idf_blocks(lines)

    for action in actions:
        action_type = action.get("action_type")
        before_count = len(report["change_log"])
        try:
            if action_type == "lighting_adjustment":
                applied = apply_lighting_action(blocks, action, strategy, report)
                if not applied:
                    report["warnings"].append("No safely editable Lights object found in this IDF.")
            elif action_type == "hvac_setpoint_adjustment":
                applied = apply_hvac_action(blocks, action, strategy, report)
                if not applied:
                    report["warnings"].append("No safely editable HVAC setpoint object found in this IDF.")
            elif action_type == "ventilation_adjustment":
                applied = apply_ventilation_action(blocks, action, strategy, report)
                if not applied:
                    report["warnings"].append("No safely editable ventilation object found in this IDF.")
            else:
                applied = False
                report["warnings"].append(f"Action type {action_type} is metadata-only for the IDF adapter.")

            if len(report["change_log"]) > before_count:
                report["actions_applied"].append(action)
            else:
                report["actions_metadata_only"].append(action)
        except Exception as exc:
            report["actions_failed"].append({"action": action, "error": str(exc)})
            report["warnings"].append(f"IDF adapter could not apply {action_type}: {exc}")

    try:
        write_blocks(target_path, blocks)
    except Exception as exc:
        report["success"] = False
        report["warnings"].append(f"Could not write target IDF: {exc}")
        return report

    report["lighting_applied"] = action_type_has_changes(report, "lighting_adjustment")
    report["hvac_setpoint_applied"] = action_type_has_changes(report, "hvac_setpoint_adjustment")
    report["ventilation_applied"] = action_type_has_changes(report, "ventilation_adjustment")
    report["success"] = target_path.exists() and bool(report["actions_applied"])
    json.dumps(report)
    return report


def copy_idf_without_changes(source_idf_path: str, target_idf_path: str) -> dict:
    source_path = Path(source_idf_path)
    target_path = Path(target_idf_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return {
        "source_idf_path": str(source_path),
        "target_idf_path": str(target_path),
        "idf_adapter_version": IDF_ADAPTER_VERSION,
        "actions_requested": [],
        "actions_applied": [],
        "actions_metadata_only": [],
        "actions_failed": [],
        "lighting_applied": False,
        "hvac_setpoint_applied": False,
        "ventilation_applied": False,
        "change_log": [],
        "warnings": ["No actions requested; copied IDF unchanged."],
        "success": True,
    }
