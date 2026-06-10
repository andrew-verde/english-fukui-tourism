# SEM Suite

This folder contains the first-pass analysis suite for survey data collected by `experiments/nudge-pilot`.

It is designed for the data you will get from either:

- local pilot CSV exports from the browser app
- Supabase CSV/JSON exports from `public.nudge_pilot_responses`

The suite does not require a dedicated SEM package. It produces the pieces needed before a full SEM:

- item-level SEM-ready task rows
- construct reliability checks
- item and construct summaries
- condition/task summaries
- construct correlations
- robust path-regression prechecks
- a mediation precheck
- a lavaan/semopy-style model specification

## Run

From the repo root:

```bash
.venv/bin/python3 experiments/sem_suite/run_sem_analysis.py \
  --input path/to/nudge_pilot_export.csv \
  --output-dir experiments/sem_suite/output
```

Generated outputs are intentionally ignored because they can contain participant-level response data.

## Input Shapes

### Local Browser CSV

The browser app exports one row per participant with columns such as:

```text
assigned_condition
survey_eiheiji_half_day_information_clarity_1
survey_eiheiji_half_day_perceived_friction_1
survey_museum_arrival_visit_intention_3
task_eiheiji_half_day_accuracy_correct
```

### Supabase Export

If you export from `public.nudge_pilot_responses`, keep the `flattened` JSON column. The runner expands it automatically.

Recommended Supabase query:

```sql
select
  study_id,
  study_version,
  session_id,
  assigned_condition,
  started_at,
  completed_at,
  flattened
from public.nudge_pilot_responses
order by completed_at;
```

Export the result as CSV or JSON, then run the suite.

## Outputs

| File | Purpose |
| --- | --- |
| `sem_analysis_rows.csv` | One row per participant-task with item columns and construct scores |
| `scale_reliability.csv` | Cronbach alpha and mean inter-item correlations |
| `item_summary.csv` | Item-level n/mean/sd/min/max |
| `construct_summary_by_condition_task.csv` | Construct means by condition and task |
| `construct_correlations.csv` | Pearson correlations among construct scores |
| `path_coefficients.csv` | Robust OLS path prechecks using construct scores |
| `mediation_precheck.csv` | Chain-mediation approximation for pilot diagnostics |
| `readiness_report.json` | Sample size and SEM readiness flags |
| `sem_summary.md` | Human-readable summary |
| `lavaan_model_spec.txt` | Full latent SEM model starting point |

## Interpretation

Use this as a pre-SEM diagnostic layer:

1. Check missingness and item distributions.
2. Check reliability. Constructs below alpha 0.70 need wording review.
3. Check whether paths point in the expected direction.
4. Only then fit a full latent-variable SEM in lavaan, semopy, jamovi, Mplus, or AMOS.

For thesis claims, the initial output should be framed as pilot evidence until you have a larger sample. The suite flags fewer than 200 participants as `pilot_only`.

With very small pilot exports, `path_coefficients.csv` may contain only a warning row for each outcome. That is intentional: the suite will not estimate overfit path models when complete rows are too sparse for the configured predictors.
