# SEM Suite

This folder contains the first-pass analysis suite for survey data collected by `experiments/nudge-pilot`.

It is designed for the data you will get from either:

- local pilot CSV exports from the browser app
- Supabase CSV/JSON exports from `public.nudge_pilot_responses`

The suite does not require a dedicated SEM package. It produces the pieces needed before a full SEM:

- item-level SEM-ready task rows
- participant-level sensitivity rows
- eligibility and exclusion diagnostics
- construct reliability checks
- item and construct summaries
- missingness and condition-balance reports
- condition/task summaries
- construct correlations
- cluster-aware robust path-regression prechecks
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

To generate a presentation-ready model-weight diagram after the analysis run:

```bash
.venv/bin/python3 experiments/sem_suite/generate_sem_path_figure.py \
  --analysis-dir experiments/sem_suite/output \
  --output experiments/sem_suite/output/sem_path_diagram.png
```

The script also writes `sem_path_diagram.svg`, which is usually the better format for slides if you want crisp scaling.

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
| `participant_score_rows.csv` | One row per participant, averaging construct scores across tasks for repeated-measures sensitivity checks |
| `eligibility_report.csv` | Participant-level schema, condition, completion, Likert range, and task-completion checks |
| `scale_reliability.csv` | Cronbach alpha and mean inter-item correlations |
| `item_summary.csv` | Item-level n/mean/sd/min/max |
| `construct_summary_by_condition_task.csv` | Construct means by condition and task |
| `missingness_report.csv` | Item-level and construct-by-condition/task missingness |
| `condition_balance.csv` | Condition counts and background-variable balance diagnostics |
| `construct_correlations.csv` | Pearson correlations among construct scores |
| `path_coefficients.csv` | Task-stacked path prechecks using cluster-robust SEs by participant when estimable |
| `participant_path_coefficients.csv` | Participant-level averaged path prechecks for repeated-task sensitivity |
| `mediation_precheck.csv` | Chain-mediation approximation for pilot diagnostics |
| `readiness_report.json` | Sample size and SEM readiness flags |
| `sem_summary.md` | Human-readable summary |
| `lavaan_model_spec.txt` | Full latent SEM model starting point |
| `sem_path_diagram.png` / `.svg` | Presentation-ready path diagram with standardized weights |

## Interpretation

Use this as a pre-SEM diagnostic layer:

1. Check `eligibility_report.csv` before looking at path coefficients.
2. Check missingness, item distributions, and condition balance.
3. Check reliability. Constructs below alpha 0.70 need wording review.
4. Check whether paths point in the expected direction.
5. Compare task-stacked and participant-level prechecks; large disagreements mean the repeated-task structure needs explicit modeling.
6. Only then fit a full latent-variable SEM in lavaan, semopy, jamovi, Mplus, or AMOS.

For thesis claims, the initial output should be framed as pilot evidence until you have a larger sample. The suite flags fewer than 300 participants as `pilot_only` by default, and the final target should be justified with Monte Carlo power simulation for the chosen SEM.

With very small pilot exports, `path_coefficients.csv` may contain only a warning row for each outcome. That is intentional: the suite will not estimate overfit path models when complete rows are too sparse for the configured predictors.

## Thesis-Readiness Notes

The experiment has repeated task responses: each participant answers the same construct items after two tourism-planning tasks. The task-stacked output is useful for diagnostics, but final claims should account for repeated measures through one of these designs:

- participant-level averaged construct scores
- cluster-robust or mixed-effects path models
- multilevel SEM
- task-specific latent factors with correlated residuals

The generated `lavaan_model_spec.txt` is a scaffold, not a final defensible SEM. Before main data collection, predefine the primary model, planned contrasts, exclusion rules, missing-data handling, and whether Likert indicators will be treated as ordered. For a final latent-variable thesis model, report CFA fit indices, standardized loadings, omega/composite reliability, discriminant validity, and indirect-effect confidence intervals from bootstrap or SEM-native estimation.

## Figure Conventions

The path diagram follows standard SEM presentation conventions:

- latent/proxy constructs are rounded ovals
- observed experimental/background predictors are rectangles
- arrows are directional structural paths
- labels show standardized beta weights where available
- thicker arrows indicate larger absolute effects
- blue arrows are positive; red arrows are negative
- dashed arrows are not significant at the selected alpha threshold
- faint gray dashed arrows are hypothesized paths shown before coefficients are estimable
- `*`, `**`, and `***` mark p-value thresholds

For categorical nudge condition effects, the diagram collapses dummy-condition paths into a readable summary arrow using the strongest absolute standardized beta and the smallest p-value for that outcome. Inspect `path_coefficients.csv` for the full dummy-coded detail.
