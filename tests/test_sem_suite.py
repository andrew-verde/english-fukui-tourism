import json
from pathlib import Path

import pandas as pd

from experiments.sem_suite.run_sem_analysis import (
    build_analysis_rows,
    load_config,
    load_response_export,
    run_analysis,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "nudge_pilot_sample.csv"
CONFIG = ROOT / "experiments" / "sem_suite" / "sem_model_config.yaml"


def test_sem_suite_builds_task_level_rows():
    config = load_config(CONFIG)
    raw = load_response_export(FIXTURE)
    analysis = build_analysis_rows(raw, config)

    assert analysis.shape[0] == 10
    assert analysis["session_id"].nunique() == 5
    assert {"information_clarity", "perceived_friction", "planning_confidence"}.issubset(analysis.columns)
    assert analysis["information_clarity"].notna().all()


def test_sem_suite_writes_expected_outputs(tmp_path):
    outputs = run_analysis(FIXTURE, tmp_path, CONFIG)

    expected = [
        "sem_analysis_rows.csv",
        "scale_reliability.csv",
        "item_summary.csv",
        "construct_summary_by_condition_task.csv",
        "construct_correlations.csv",
        "path_coefficients.csv",
        "mediation_precheck.csv",
        "readiness_report.json",
        "sem_summary.md",
        "lavaan_model_spec.txt",
    ]
    for name in expected:
        assert (tmp_path / name).exists()

    readiness = json.loads((tmp_path / "readiness_report.json").read_text(encoding="utf-8"))
    assert readiness["n_participants"] == 5
    assert readiness["minimum_sem_status"] == "pilot_only"
    assert outputs.reliability["construct"].nunique() == 5


def test_sem_suite_expands_supabase_flattened_column(tmp_path):
    raw = pd.read_csv(FIXTURE)
    rows = []
    for _, row in raw.iterrows():
        rows.append(
            {
                "study_id": row["study_id"],
                "study_version": row["version"],
                "session_id": row["session_id"],
                "assigned_condition": row["assigned_condition"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "flattened": json.dumps(row.to_dict()),
            }
        )
    export = tmp_path / "supabase_export.csv"
    pd.DataFrame(rows).to_csv(export, index=False)

    config = load_config(CONFIG)
    expanded = load_response_export(export)
    analysis = build_analysis_rows(expanded, config)

    assert analysis.shape[0] == 10
    assert "visit_intention" in analysis.columns
