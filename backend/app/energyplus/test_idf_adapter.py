import json
import shutil
from pathlib import Path

from backend.app.energyplus.config import DEFAULT_MODEL
from backend.app.energyplus.idf_adapter import apply_action_bundle_to_idf


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEST_DIR = PROJECT_ROOT / "artifacts" / "layer_5_closed_loop" / "idf_adapter_test"


SAMPLE_IDF = """Version, 26.1;

Lights,
  Test Lights,              !- Name
  Test Zone,                !- Zone or ZoneList Name
  Always On,                !- Schedule Name
  LightingLevel,            !- Design Level Calculation Method
  1000,                     !- Lighting Level {W}
  ,                         !- Watts per Zone Floor Area {W/m2}
  ;                         !- Watts per Person {W/person}

Schedule:Compact,
  Test Cooling Setpoint,    !- Name
  Temperature,              !- Schedule Type Limits Name
  Through: 12/31,
  For: AllDays,
  Until: 24:00, 24;

Schedule:Compact,
  Test Outdoor Air Schedule,!- Name
  Fraction,                 !- Schedule Type Limits Name
  Through: 12/31,
  For: AllDays,
  Until: 24:00, 1.0;

Schedule:Compact,
  OA Cooling Supply Air Temp Sch,
  Temperature,
  Through: 12/31,
  For: AllDays,
  Until: 24:00, 12.8;

DesignSpecification:OutdoorAir,
  Test OA,                  !- Name
  Flow/Person,              !- Outdoor Air Method
  0.00944,                  !- Outdoor Air Flow per Person {m3/s-person}
  0.0,                      !- Outdoor Air Flow per Zone Floor Area
  0.0,                      !- Outdoor Air Flow per Zone
  0.0;                      !- Outdoor Air Flow Air Changes per Hour
"""


def prepare_source_idf(source: Path) -> str:
    if DEFAULT_MODEL.exists():
        shutil.copy2(DEFAULT_MODEL, source)
        return f"Copied configured demo IDF from {DEFAULT_MODEL}."
    source.write_text(SAMPLE_IDF)
    return "Configured demo IDF missing; wrote synthetic IDF with Lights, HVAC setpoint, and outdoor air objects."


def action_is_metadata_only(report: dict, action_type: str) -> bool:
    return any(action.get("action_type") == action_type for action in report.get("actions_metadata_only", []))


def warning_contains(report: dict, text: str) -> bool:
    return any(text in warning for warning in report.get("warnings", []))


if __name__ == "__main__":
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    source = TEST_DIR / "source.idf"
    target = TEST_DIR / "target.idf"
    if target.exists():
        target.unlink()
    source_note = prepare_source_idf(source)
    original = source.read_text()

    bundle = {
        "bundle_name": "idf_adapter_test_bundle",
        "actions": [
            {
                "action_type": "lighting_adjustment",
                "target": "unoccupied_zones",
                "parameters": {"lighting_level_percent": 25},
            },
            {
                "action_type": "hvac_setpoint_adjustment",
                "target": "unoccupied_zones",
                "parameters": {"cooling_setpoint_c": 28},
            },
            {
                "action_type": "ventilation_adjustment",
                "target": "unoccupied_zones",
                "parameters": {"ventilation_percent": 40},
            },
        ],
    }

    report = apply_action_bundle_to_idf(str(source), str(target), bundle)
    print(json.dumps({"source_note": source_note, "report": report}, indent=2))

    assert target.exists()
    assert source.read_text() == original
    if report["actions_applied"]:
        assert target.read_text() != original
    assert report["actions_applied"]
    assert isinstance(report["actions_metadata_only"], list)
    assert isinstance(report["change_log"], list)
    assert isinstance(report["warnings"], list)
    assert report["success"] is True
    assert report["lighting_applied"] is True
    assert target.read_text() != original
    assert report["hvac_setpoint_applied"] is True or any(
        "No safely editable HVAC setpoint object found" in warning for warning in report["warnings"]
    )
    if not report["hvac_setpoint_applied"]:
        assert action_is_metadata_only(report, "hvac_setpoint_adjustment")
        assert warning_contains(report, "No safely editable HVAC setpoint object found in this IDF.")
    assert report["ventilation_applied"] is True or any(
        "No safely editable ventilation object found" in warning for warning in report["warnings"]
    )
    if not report["ventilation_applied"]:
        assert action_is_metadata_only(report, "ventilation_adjustment")
        assert warning_contains(report, "No safely editable ventilation object found in this IDF.")
    else:
        forbidden_name_terms = ("temp", "temperature", "supply air temp", "heating supply air", "cooling supply air")
        ventilation_changes = [
            change
            for change in report["change_log"]
            if change.get("action_type") == "ventilation_adjustment"
        ]
        assert ventilation_changes
        for change in ventilation_changes:
            name = change.get("object_name", "").lower()
            assert not any(term in name for term in forbidden_name_terms)
            assert change["new_value"] <= change["old_value"]
            assert change["multiplier"] == 0.4
            if change.get("object_type") == "DesignSpecification:OutdoorAir" and change["old_value"] > 0:
                assert abs(change["new_value"] - (change["old_value"] * 0.4)) < 0.00001
        assert not any(
            change.get("object_type", "").lower().startswith("schedule:")
            for change in ventilation_changes
        )
    assert any(change["action_type"] == "lighting_adjustment" for change in report["change_log"])
    json.dumps(report)

    increase_target = TEST_DIR / "target_increase.idf"
    increase_bundle = {
        "bundle_name": "iaq_recovery",
        "actions": [{
            "action_type": "ventilation_adjustment",
            "target": "occupied_zones",
            "parameters": {"ventilation_multiplier": 1.2},
        }],
    }
    increase_report = apply_action_bundle_to_idf(str(source), str(increase_target), increase_bundle)
    increase_changes = [
        change for change in increase_report["change_log"]
        if change.get("action_type") == "ventilation_adjustment"
    ]
    assert increase_changes
    assert all(change["new_value"] > change["old_value"] for change in increase_changes)
    assert all(change["multiplier"] == 1.2 for change in increase_changes)
    assert not any(
        change.get("object_type", "").lower().startswith("schedule:")
        for change in increase_changes
    )

    print("\nPhase 5.7 IDF adapter test passed.")
