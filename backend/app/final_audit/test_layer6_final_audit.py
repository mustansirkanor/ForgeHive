import json
from pathlib import Path

from backend.app.closed_loop.real_llm_full_loop import ollama_is_reachable, openrouter_key_present
from backend.app.final_audit.submission_report import build_final_submission_report
from backend.app.final_audit.test_matrix import classify_test_result


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "final_submission"


if __name__ == "__main__":
    assert classify_test_result(
        "python -m backend.app.closed_loop.test_feedback_learner",
        0,
        '{"learning_status": "skipped", "learning_notes": ["Memory update skipped because execution did not succeed."]}',
        "",
    ) == "passed"
    assert classify_test_result("python -m some.test", 1, "TEST_SKIPPED", "") == "failed"
    assert classify_test_result("python -m some.test", 0, "TEST_SKIPPED", "") == "skipped"

    package = build_final_submission_report()
    print(json.dumps(package, indent=2))

    generated = package.get("generated_files", {})
    assert Path(generated["final_submission_package"]).exists()
    assert Path(generated["final_audit"]).exists()
    assert Path(generated["artifact_audit"]).exists()
    assert Path(generated["demo_audit"]).exists()
    assert Path(generated["readiness_score"]).exists()
    assert Path(generated["judge_summary"]).exists()
    assert Path(generated["demo_script"]).exists()

    assert package.get("test_matrix")
    assert package.get("artifact_audit")
    assert package.get("demo_audit")
    assert package.get("readiness_score")
    assert package.get("real_building_execution") is False

    demo = package["demo_audit"].get("demo_result", {})
    selected_provider = demo.get("selected_provider")
    real_provider_available = ollama_is_reachable() or openrouter_key_present()
    if selected_provider == "mock":
        package["readiness_score"].setdefault("risks", []).append("Final demo used mock provider.")
        if real_provider_available:
            raise AssertionError("Real provider is available but final demo selected mock.")

    assert demo.get("real_building_execution") is False
    assert package["readiness_score"]["score"] >= 75
    assert (PROJECT_ROOT / "docs" / "FINAL_JUDGE_NARRATIVE.md").exists()
    assert (PROJECT_ROOT / "docs" / "FINAL_DEMO_SCRIPT.md").exists()

    print("\nLayer 6 final audit passed: ForgeHive is ready for final demo review.")
