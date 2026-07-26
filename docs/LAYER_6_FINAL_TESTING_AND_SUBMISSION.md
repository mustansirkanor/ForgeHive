# ForgeHive Layer 6 Final Testing And Submission

Layer 6 is the final audit layer for ForgeHive. It verifies tests, proof artifacts, real-provider demo readiness, EnergyPlus execution, Safety Governor boundaries, IDF adapter honesty, and final judge-facing submission materials.

## What Layer 6 Runs

- Complete automated test matrix across Layers 1-5
- Artifact existence and JSON validity audit
- Final real LLM full-loop demo audit
- Readiness score calculation
- Final demo script generation
- Final judge narrative generation
- Final submission package export

## Main Command

```bash
python -m backend.app.final_audit.test_layer6_final_audit
```

## Output Artifacts

Generated under `artifacts/final_submission/`:

- `forgehive_final_audit.json`
- `forgehive_artifact_audit.json`
- `forgehive_final_demo_audit.json`
- `forgehive_demo_script.md`
- `forgehive_judge_summary.md`
- `forgehive_readiness_score.json`
- `forgehive_final_submission_package.json`
- `forgehive_test_matrix.json`

## Readiness Score

The readiness score is out of 100:

- Test pass rate: 30
- Artifact completeness: 20
- Real LLM demo proven: 15
- EnergyPlus closed-loop execution: 15
- Safety/guardrails proof: 10
- Learning loop proof: 5
- Presentation readiness: 5

## Safety

Layer 6 must preserve ForgeHive's safety boundary:

- no real building execution;
- Safety Governor remains active;
- rejected actions are not executed;
- EnergyPlus digital twin is the execution target;
- API keys are redacted from captured test output.

## Manual Review

After running the audit, inspect:

- `artifacts/final_submission/forgehive_readiness_score.json`
- `artifacts/final_submission/forgehive_judge_summary.md`
- `artifacts/final_submission/forgehive_demo_script.md`
- `artifacts/final_submission/forgehive_final_submission_package.json`
