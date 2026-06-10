#!/usr/bin/env python3
"""Run an initial SEM-style analysis pass for the nudge pilot.

This runner is intentionally conservative: it does not require a dedicated SEM
package. It prepares SEM-ready item-level data, checks scale reliability, scores
latent-construct proxies, and estimates a path model with robust standard
errors. The output can be used directly for a pilot report or as preflight data
for lavaan/semopy later.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy import stats

try:
    import statsmodels.api as sm
except ImportError:  # pragma: no cover - requirements include statsmodels in this env.
    sm = None


DEFAULT_CONFIG = Path(__file__).with_name("sem_model_config.yaml")


@dataclass
class SemOutputs:
    analysis_rows: pd.DataFrame
    participant_scores: pd.DataFrame
    eligibility: pd.DataFrame
    reliability: pd.DataFrame
    item_summary: pd.DataFrame
    construct_summary: pd.DataFrame
    missingness: pd.DataFrame
    condition_balance: pd.DataFrame
    correlations: pd.DataFrame
    path_coefficients: pd.DataFrame
    participant_path_coefficients: pd.DataFrame
    mediation: pd.DataFrame
    readiness: dict[str, Any]


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_response_export(path: Path) -> pd.DataFrame:
    """Load local app CSV, Supabase table CSV, or Supabase JSON export."""
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "data" in raw:
            raw = raw["data"]
        if not isinstance(raw, list):
            raise ValueError("JSON input must be a list of response records")
        df = pd.DataFrame(raw)
    else:
        df = pd.read_csv(path)

    return expand_flattened_column(df)


def expand_flattened_column(df: pd.DataFrame) -> pd.DataFrame:
    """Expand Supabase's `flattened` JSON column when present."""
    if "flattened" not in df.columns:
        return df.copy()

    expanded_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        base = row.drop(labels=["flattened"]).to_dict()
        flattened = row["flattened"]
        if isinstance(flattened, str) and flattened.strip():
            flattened_obj = json.loads(flattened)
        elif isinstance(flattened, dict):
            flattened_obj = flattened
        else:
            flattened_obj = {}
        base.update(flattened_obj)
        expanded_rows.append(base)
    return pd.DataFrame(expanded_rows)


def build_analysis_rows(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Create one analysis row per participant-task."""
    rows: list[dict[str, Any]] = []
    task_ids = config["task_ids"]

    for _, participant in df.iterrows():
        common = {
            "study_id": participant.get("study_id"),
            "version": participant.get("version") or participant.get("study_version"),
            "session_id": participant.get("session_id"),
            "assigned_condition": participant.get("assigned_condition"),
            "started_at": participant.get("started_at"),
            "completed_at": participant.get("completed_at"),
        }
        for col in df.columns:
            if col.startswith("background_"):
                common[col] = participant.get(col)

        for task_id in task_ids:
            row = dict(common)
            row["task_id"] = task_id
            for col in df.columns:
                task_prefix = f"task_{task_id}_"
                survey_prefix = f"survey_{task_id}_"
                if col.startswith(task_prefix):
                    row[col.replace(task_prefix, "task_")] = participant.get(col)
                elif col.startswith(survey_prefix):
                    row[col.replace(survey_prefix, "")] = participant.get(col)
            if any(item in row for construct in config["constructs"].values() for item in construct["item_suffixes"]):
                rows.append(row)

    analysis = pd.DataFrame(rows)
    if analysis.empty:
        raise ValueError("No task-level survey rows were found. Check input columns and task_ids.")

    analysis = normalize_columns(analysis)
    return score_constructs(analysis, config)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    numeric_candidates = [
        "background_public_transit_confidence",
        "task_time_on_task_ms",
    ]
    numeric_candidates.extend([col for col in out.columns if col.endswith(("_1", "_2", "_3"))])
    for col in numeric_candidates:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    familiarity = {
        "Not familiar": 1,
        "Heard of it": 2,
        "Somewhat familiar": 3,
        "Very familiar": 4,
    }
    if "background_fukui_familiarity" in out.columns:
        out["background_fukui_familiarity"] = out["background_fukui_familiarity"].map(familiarity).fillna(
            pd.to_numeric(out["background_fukui_familiarity"], errors="coerce")
        )
    if "task_accuracy_correct" in out.columns:
        out["task_accuracy_correct"] = out["task_accuracy_correct"].map(
            lambda value: str(value).lower() in {"true", "1", "yes"}
        )
    return out


def score_constructs(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    for construct_id, construct in config["constructs"].items():
        items = [item for item in construct["item_suffixes"] if item in out.columns]
        if items:
            out[construct_id] = out[items].mean(axis=1, skipna=False)
    return out


def expected_item_columns(config: dict[str, Any], task_id: str | None = None) -> list[str]:
    items = [item for construct in config["constructs"].values() for item in construct["item_suffixes"]]
    if task_id is None:
        return items
    return [f"survey_{task_id}_{item}" for item in items]


def eligibility_table(raw: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Participant-level eligibility checks before any SEM precheck."""
    rows = []
    task_ids = config["task_ids"]
    condition_order = set(config.get("condition_order", []))
    expected_study = config.get("study_id")

    for _, participant in raw.iterrows():
        reasons = []
        session_id = participant.get("session_id")
        assigned_condition = participant.get(config["condition_column"])
        if not session_id:
            reasons.append("missing_session_id")
        if expected_study and participant.get("study_id") != expected_study:
            reasons.append("unexpected_study_id")
        if assigned_condition not in condition_order:
            reasons.append("unexpected_condition")
        completed_at = participant.get("completed_at")
        if pd.isna(completed_at) or completed_at == "":
            reasons.append("missing_completed_at")

        completed_tasks = 0
        complete_task_surveys = 0
        out_of_range_items = 0
        missing_items = 0
        task_accuracy_values = []
        for task_id in task_ids:
            task_cols = [col for col in raw.columns if col.startswith(f"task_{task_id}_")]
            survey_cols = expected_item_columns(config, task_id)
            completed_tasks += int(any(pd.notna(participant.get(col)) and participant.get(col) != "" for col in task_cols))

            task_values = []
            for col in survey_cols:
                value = pd.to_numeric(pd.Series([participant.get(col)]), errors="coerce").iloc[0]
                task_values.append(value)
                if pd.isna(value):
                    missing_items += 1
                elif value < 1 or value > 7:
                    out_of_range_items += 1
            complete_task_surveys += int(all(not pd.isna(value) for value in task_values))

            accuracy_col = f"task_{task_id}_accuracy_correct"
            if accuracy_col in raw.columns:
                task_accuracy_values.append(str(participant.get(accuracy_col)).lower() in {"true", "1", "yes"})

        if completed_tasks < len(task_ids):
            reasons.append("missing_task_response")
        if complete_task_surveys < len(task_ids):
            reasons.append("incomplete_task_survey")
        if out_of_range_items:
            reasons.append("likert_out_of_range")

        rows.append(
            {
                "session_id": session_id,
                "assigned_condition": assigned_condition,
                "completed_tasks": completed_tasks,
                "complete_task_surveys": complete_task_surveys,
                "missing_likert_items": missing_items,
                "out_of_range_likert_items": out_of_range_items,
                "all_accuracy_correct": bool(task_accuracy_values) and all(task_accuracy_values),
                "sem_eligible": len(reasons) == 0,
                "exclusion_reasons": ";".join(reasons),
            }
        )
    return pd.DataFrame(rows)


def participant_score_rows(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Average task-level construct scores to one row per participant."""
    if "session_id" not in df.columns:
        return pd.DataFrame()
    construct_ids = [construct_id for construct_id in config["constructs"] if construct_id in df.columns]
    rows = []
    for session_id, group in df.groupby("session_id", dropna=False):
        first = group.iloc[0]
        row: dict[str, Any] = {
            "session_id": session_id,
            "assigned_condition": first.get("assigned_condition"),
            "n_task_rows": int(group.shape[0]),
        }
        for col in group.columns:
            if col.startswith("background_"):
                row[col] = first.get(col)
        for construct_id in construct_ids:
            row[construct_id] = pd.to_numeric(group[construct_id], errors="coerce").mean()
        if "task_accuracy_correct" in group.columns:
            row["task_accuracy_rate"] = pd.to_numeric(group["task_accuracy_correct"], errors="coerce").mean()
        if "task_time_on_task_ms" in group.columns:
            row["task_time_on_task_ms_mean"] = pd.to_numeric(group["task_time_on_task_ms"], errors="coerce").mean()
        rows.append(row)
    return pd.DataFrame(rows)


def cronbach_alpha(items_df: pd.DataFrame) -> float:
    clean = items_df.dropna()
    if clean.shape[0] < 2 or clean.shape[1] < 2:
        return math.nan
    item_variances = clean.var(axis=0, ddof=1)
    total_variance = clean.sum(axis=1).var(ddof=1)
    if total_variance == 0 or pd.isna(total_variance):
        return math.nan
    n_items = clean.shape[1]
    return float((n_items / (n_items - 1)) * (1 - item_variances.sum() / total_variance))


def reliability_table(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for construct_id, construct in config["constructs"].items():
        items = [item for item in construct["item_suffixes"] if item in df.columns]
        item_df = df[items].apply(pd.to_numeric, errors="coerce") if items else pd.DataFrame()
        rows.append(
            {
                "construct": construct_id,
                "label": construct["label"],
                "n_items": len(items),
                "n_complete": int(item_df.dropna().shape[0]) if items else 0,
                "cronbach_alpha": cronbach_alpha(item_df) if items else math.nan,
                "mean_inter_item_correlation": mean_inter_item_correlation(item_df),
            }
        )
    return pd.DataFrame(rows)


def mean_inter_item_correlation(item_df: pd.DataFrame) -> float:
    clean = item_df.dropna()
    if clean.shape[0] < 2 or clean.shape[1] < 2:
        return math.nan
    corr = clean.corr()
    mask = np.triu(np.ones(corr.shape), k=1).astype(bool)
    values = corr.where(mask).stack()
    return float(values.mean()) if not values.empty else math.nan


def item_summary_table(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for construct_id, construct in config["constructs"].items():
        for item in construct["item_suffixes"]:
            if item not in df.columns:
                rows.append({"construct": construct_id, "item": item, "n": 0})
                continue
            series = pd.to_numeric(df[item], errors="coerce")
            rows.append(
                {
                    "construct": construct_id,
                    "item": item,
                    "n": int(series.notna().sum()),
                    "mean": series.mean(),
                    "sd": series.std(ddof=1),
                    "min": series.min(),
                    "max": series.max(),
                }
            )
    return pd.DataFrame(rows)


def missingness_table(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    total_n = int(df.shape[0])
    for construct_id, construct in config["constructs"].items():
        for item in construct["item_suffixes"]:
            if item not in df.columns:
                rows.append(
                    {
                        "scope": "item",
                        "construct": construct_id,
                        "variable": item,
                        "n": total_n,
                        "n_missing": total_n,
                        "pct_missing": 1.0 if total_n else math.nan,
                    }
                )
                continue
            series = pd.to_numeric(df[item], errors="coerce")
            n_missing = int(series.isna().sum())
            rows.append(
                {
                    "scope": "item",
                    "construct": construct_id,
                    "variable": item,
                    "n": total_n,
                    "n_missing": n_missing,
                    "pct_missing": n_missing / total_n if total_n else math.nan,
                }
            )
    group_cols = [col for col in ["assigned_condition", "task_id"] if col in df.columns]
    for keys, group in df.groupby(group_cols, dropna=False) if group_cols else []:
        key_values = keys if isinstance(keys, tuple) else (keys,)
        label = ", ".join(f"{col}={value}" for col, value in zip(group_cols, key_values))
        for construct_id in config["constructs"]:
            if construct_id not in group.columns:
                continue
            series = pd.to_numeric(group[construct_id], errors="coerce")
            n_missing = int(series.isna().sum())
            rows.append(
                {
                    "scope": "construct_by_group",
                    "construct": construct_id,
                    "variable": label,
                    "n": int(group.shape[0]),
                    "n_missing": n_missing,
                    "pct_missing": n_missing / group.shape[0] if group.shape[0] else math.nan,
                }
            )
    return pd.DataFrame(rows)


def condition_balance_table(raw: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    condition_col = config["condition_column"]
    if condition_col not in raw.columns:
        return pd.DataFrame()
    rows = []
    participant_rows = raw.drop_duplicates("session_id") if "session_id" in raw.columns else raw
    total_n = int(participant_rows.shape[0])
    counts = participant_rows[condition_col].value_counts(dropna=False)
    expected = total_n / max(len(config.get("condition_order", [])), 1)
    for condition in config.get("condition_order", counts.index.tolist()):
        count = int(counts.get(condition, 0))
        rows.append(
            {
                "scope": "condition_count",
                "variable": condition,
                "level": condition,
                "n": count,
                "proportion": count / total_n if total_n else math.nan,
                "expected_even_n": expected,
                "difference_from_even_n": count - expected,
            }
        )
    background_cols = [col for col in participant_rows.columns if col.startswith("background_")]
    for background_col in background_cols:
        numeric_values = pd.to_numeric(participant_rows[background_col], errors="coerce")
        non_empty = participant_rows[background_col].notna() & (participant_rows[background_col] != "")
        if non_empty.any() and numeric_values[non_empty].notna().all():
            grouped = numeric_values.groupby(participant_rows[condition_col])
            for condition, values in grouped:
                rows.append(
                    {
                        "scope": "background_mean",
                        "variable": background_col,
                        "level": condition,
                        "n": int(values.notna().sum()),
                        "mean": values.mean(),
                        "sd": values.std(ddof=1),
                    }
                )
        else:
            grouped = participant_rows.groupby([condition_col, background_col], dropna=False).size()
            for (condition, level), count in grouped.items():
                rows.append(
                    {
                        "scope": "background_level",
                        "variable": background_col,
                        "level": f"{condition}:{level}",
                        "n": int(count),
                        "proportion": count / total_n if total_n else math.nan,
                    }
                )
    return pd.DataFrame(rows)


def construct_summary_table(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    group_cols = ["assigned_condition", "task_id"]
    for keys, group in df.groupby(group_cols, dropna=False):
        condition, task_id = keys
        for construct_id in config["constructs"]:
            if construct_id not in group.columns:
                continue
            series = pd.to_numeric(group[construct_id], errors="coerce")
            rows.append(
                {
                    "assigned_condition": condition,
                    "task_id": task_id,
                    "construct": construct_id,
                    "n": int(series.notna().sum()),
                    "mean": series.mean(),
                    "sd": series.std(ddof=1),
                    "median": series.median(),
                }
            )
    return pd.DataFrame(rows)


def correlation_table(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    constructs = [construct for construct in config["constructs"] if construct in df.columns]
    rows = []
    for i, left in enumerate(constructs):
        for right in constructs[i + 1 :]:
            pair = df[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
            if pair.shape[0] < 3:
                r, p = math.nan, math.nan
            else:
                r, p = stats.pearsonr(pair[left], pair[right])
            rows.append({"left": left, "right": right, "n": int(pair.shape[0]), "pearson_r": r, "p_value": p})
    return pd.DataFrame(rows)


def path_coefficients(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if sm is None:
        return pd.DataFrame()
    rows = []
    for model in config["path_model"]:
        outcome = model["outcome"]
        if outcome not in df.columns:
            continue
        model_df, predictor_cols = design_matrix(df, model["predictors"], outcome, config)
        if model_df.shape[0] < len(predictor_cols) + 5:
            rows.append(
                {
                    "outcome": outcome,
                    "predictor": "__model__",
                    "n": int(model_df.shape[0]),
                    "warning": "Too few complete rows for stable model",
                }
            )
            continue
        y = pd.to_numeric(model_df[outcome], errors="coerce")
        x = sm.add_constant(model_df[predictor_cols], has_constant="add")
        cluster_col = "__cluster_group"
        n_clusters = int(model_df[cluster_col].nunique()) if cluster_col in model_df.columns else 0
        if n_clusters >= len(predictor_cols) + 2:
            fitted = sm.OLS(y, x).fit(cov_type="cluster", cov_kwds={"groups": model_df[cluster_col]})
            covariance = "cluster_session"
        else:
            fitted = sm.OLS(y, x).fit(cov_type="HC3")
            covariance = "HC3"
        y_sd = y.std(ddof=1)
        predictor_sds = model_df[predictor_cols].std(ddof=1)
        for predictor in fitted.params.index:
            standardized_beta = math.nan
            if predictor != "const" and y_sd and not pd.isna(y_sd):
                x_sd = predictor_sds.get(predictor, math.nan)
                if x_sd and not pd.isna(x_sd):
                    standardized_beta = fitted.params[predictor] * (x_sd / y_sd)
            rows.append(
                {
                    "outcome": outcome,
                    "predictor": predictor,
                    "n": int(fitted.nobs),
                    "coef": fitted.params[predictor],
                    "standardized_beta": standardized_beta,
                    "std_err": fitted.bse[predictor],
                    "t_value": fitted.tvalues[predictor],
                    "p_value": fitted.pvalues[predictor],
                    "r_squared": fitted.rsquared,
                    "covariance": covariance,
                    "n_clusters": n_clusters if n_clusters else math.nan,
                    "warning": "",
                }
            )
    return pd.DataFrame(rows)


def design_matrix(
    df: pd.DataFrame, predictors: list[str], outcome: str, config: dict[str, Any]
) -> tuple[pd.DataFrame, list[str]]:
    parts = [pd.to_numeric(df[outcome], errors="coerce").rename(outcome)]
    predictor_cols: list[str] = []
    condition_col = config["condition_column"]
    condition_reference = config.get("condition_reference", "control")
    cluster_col = config.get("cluster_column", "session_id")

    for predictor in predictors:
        if predictor == "condition":
            dummies = pd.get_dummies(df[condition_col], prefix="condition", dtype=float)
            ref_col = f"condition_{condition_reference}"
            dummies = dummies.drop(columns=[ref_col], errors="ignore")
            parts.append(dummies)
            predictor_cols.extend(dummies.columns.tolist())
        elif predictor in df.columns:
            series = pd.to_numeric(df[predictor], errors="coerce").rename(predictor)
            parts.append(series)
            predictor_cols.append(predictor)
    if cluster_col in df.columns:
        parts.append(df[cluster_col].rename("__cluster_group"))
    model_df = pd.concat(parts, axis=1).dropna()
    return model_df, predictor_cols


def mediation_table(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for check in config.get("mediation_checks", []):
        needed = [check["x"], check["mediator_1"], check["mediator_2"], check["y"]]
        if not all(col in df.columns for col in needed):
            continue
        clean = df[needed].apply(pd.to_numeric, errors="coerce").dropna()
        if clean.shape[0] < 20 or sm is None:
            rows.append({"name": check["name"], "n": int(clean.shape[0]), "warning": "Too few rows for mediation precheck"})
            continue
        a1 = sm.OLS(clean[check["mediator_1"]], sm.add_constant(clean[[check["x"]]])).fit(cov_type="HC3")
        a2 = sm.OLS(clean[check["mediator_2"]], sm.add_constant(clean[[check["x"], check["mediator_1"]]])).fit(
            cov_type="HC3"
        )
        b = sm.OLS(
            clean[check["y"]],
            sm.add_constant(clean[[check["x"], check["mediator_1"], check["mediator_2"]]]),
        ).fit(cov_type="HC3")
        indirect_chain = (
            a1.params.get(check["x"], math.nan)
            * a2.params.get(check["mediator_1"], math.nan)
            * b.params.get(check["mediator_2"], math.nan)
        )
        rows.append(
            {
                "name": check["name"],
                "n": int(clean.shape[0]),
                "a_x_to_m1": a1.params.get(check["x"], math.nan),
                "d_m1_to_m2": a2.params.get(check["mediator_1"], math.nan),
                "b_m2_to_y": b.params.get(check["mediator_2"], math.nan),
                "direct_x_to_y": b.params.get(check["x"], math.nan),
                "chain_indirect_estimate": indirect_chain,
                "warning": "Pilot precheck only; use bootstrap SEM/mediation for final claims",
            }
        )
    return pd.DataFrame(rows)


def readiness_report(
    df: pd.DataFrame, reliability: pd.DataFrame, config: dict[str, Any], eligibility: pd.DataFrame | None = None
) -> dict[str, Any]:
    n_participants = int(df["session_id"].nunique()) if "session_id" in df.columns else 0
    n_task_rows = int(df.shape[0])
    expected_task_rows = n_participants * len(config.get("task_ids", []))
    condition_counts = (
        df.drop_duplicates("session_id")["assigned_condition"].value_counts(dropna=False).to_dict()
        if "session_id" in df.columns
        else {}
    )
    low_reliability = reliability[
        reliability["cronbach_alpha"].notna() & (reliability["cronbach_alpha"] < 0.7)
    ]["construct"].tolist()
    minimum_participants = int(config.get("minimum_participants_for_sem", 300))
    n_constructs = len(config.get("constructs", {}))
    n_indicators = sum(len(construct.get("item_suffixes", [])) for construct in config.get("constructs", {}).values())
    n_sem_eligible = (
        int(eligibility["sem_eligible"].fillna(False).sum())
        if eligibility is not None and "sem_eligible" in eligibility.columns
        else n_participants
    )
    ineligible_reasons: dict[str, int] = {}
    if eligibility is not None and "exclusion_reasons" in eligibility.columns:
        for reason_group in eligibility["exclusion_reasons"].dropna():
            for reason in str(reason_group).split(";"):
                if reason:
                    ineligible_reasons[reason] = ineligible_reasons.get(reason, 0) + 1
    return {
        "n_participants": n_participants,
        "n_sem_eligible_participants": n_sem_eligible,
        "sem_eligible_participant_rate": n_sem_eligible / n_participants if n_participants else math.nan,
        "ineligible_participants": n_participants - n_sem_eligible,
        "ineligible_reasons": ineligible_reasons,
        "n_task_rows": n_task_rows,
        "expected_task_rows": expected_task_rows,
        "complete_task_row_rate": n_task_rows / expected_task_rows if expected_task_rows else math.nan,
        "condition_counts": condition_counts,
        "constructs_below_alpha_0_70": low_reliability,
        "measurement_model_indicators": n_indicators,
        "structural_constructs": n_constructs,
        "minimum_sem_status": "pilot_only" if n_participants < minimum_participants else "candidate_for_sem",
        "recommended_next_sample_target": minimum_participants if n_participants < minimum_participants else minimum_participants + 100,
        "planned_contrasts": config.get("planned_contrasts", []),
        "notes": [
            "Use this as an initial SEM readiness pass, not final causal evidence.",
            "Inspect item distributions and reliability before fitting a full latent-variable SEM.",
            "Task-level path prechecks use cluster-robust standard errors by participant when enough clusters are available.",
            "Use participant-level rows as a sensitivity check for repeated-task non-independence.",
            "Keep item-level columns for lavaan/semopy; construct means are proxies for path prechecks.",
            config.get("main_sample_note", ""),
        ],
    }


def write_lavaan_spec(config: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# Measurement model",
        "# This scaffold assumes one row per participant-task.",
        "# For final thesis SEM, choose either participant-level averaged rows,",
        "# multilevel SEM, or task-specific latent factors with correlated residuals.",
    ]
    for construct_id, construct in config["constructs"].items():
        lines.append(f"{construct_id} =~ " + " + ".join(construct["item_suffixes"]))
    lines.extend(["", "# Structural model"])
    for model in config["path_model"]:
        predictors = []
        for predictor in model["predictors"]:
            predictors.append("condition_dummies" if predictor == "condition" else predictor)
        lines.append(f"{model['outcome']} ~ " + " + ".join(predictors))
    lines.append("")
    lines.append("# Replace condition_dummies with explicit dummy columns after export.")
    lines.append("# Use WLSMV/ordinal indicators in lavaan if treating Likert items as ordered.")
    lines.append("# Add cluster = session_id or an equivalent repeated-measures structure before final claims.")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_analysis(input_path: Path, output_dir: Path, config_path: Path = DEFAULT_CONFIG) -> SemOutputs:
    config = load_config(config_path)
    raw = load_response_export(input_path)
    analysis_rows = build_analysis_rows(raw, config)
    eligibility = eligibility_table(raw, config)
    if "session_id" in analysis_rows.columns and not eligibility.empty:
        analysis_rows = analysis_rows.merge(
            eligibility[["session_id", "sem_eligible", "exclusion_reasons"]],
            on="session_id",
            how="left",
        )
    eligible_rows = analysis_rows[analysis_rows["sem_eligible"].fillna(True)].copy() if "sem_eligible" in analysis_rows.columns else analysis_rows
    participant_scores = participant_score_rows(eligible_rows, config)
    reliability = reliability_table(analysis_rows, config)
    item_summary = item_summary_table(analysis_rows, config)
    construct_summary = construct_summary_table(analysis_rows, config)
    missingness = missingness_table(analysis_rows, config)
    condition_balance = condition_balance_table(raw, config)
    correlations = correlation_table(eligible_rows, config)
    paths = path_coefficients(eligible_rows, config)
    participant_paths = path_coefficients(participant_scores, config) if not participant_scores.empty else pd.DataFrame()
    mediation = mediation_table(eligible_rows, config)
    readiness = readiness_report(analysis_rows, reliability, config, eligibility)

    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_rows.to_csv(output_dir / "sem_analysis_rows.csv", index=False)
    participant_scores.to_csv(output_dir / "participant_score_rows.csv", index=False)
    eligibility.to_csv(output_dir / "eligibility_report.csv", index=False)
    reliability.to_csv(output_dir / "scale_reliability.csv", index=False)
    item_summary.to_csv(output_dir / "item_summary.csv", index=False)
    construct_summary.to_csv(output_dir / "construct_summary_by_condition_task.csv", index=False)
    missingness.to_csv(output_dir / "missingness_report.csv", index=False)
    condition_balance.to_csv(output_dir / "condition_balance.csv", index=False)
    correlations.to_csv(output_dir / "construct_correlations.csv", index=False)
    paths.to_csv(output_dir / "path_coefficients.csv", index=False)
    participant_paths.to_csv(output_dir / "participant_path_coefficients.csv", index=False)
    mediation.to_csv(output_dir / "mediation_precheck.csv", index=False)
    (output_dir / "readiness_report.json").write_text(json.dumps(readiness, indent=2), encoding="utf-8")
    write_markdown_summary(output_dir / "sem_summary.md", readiness, reliability, paths)
    write_lavaan_spec(config, output_dir / "lavaan_model_spec.txt")

    return SemOutputs(
        analysis_rows=analysis_rows,
        participant_scores=participant_scores,
        eligibility=eligibility,
        reliability=reliability,
        item_summary=item_summary,
        construct_summary=construct_summary,
        missingness=missingness,
        condition_balance=condition_balance,
        correlations=correlations,
        path_coefficients=paths,
        participant_path_coefficients=participant_paths,
        mediation=mediation,
        readiness=readiness,
    )


def write_markdown_summary(path: Path, readiness: dict[str, Any], reliability: pd.DataFrame, paths: pd.DataFrame) -> None:
    lines = [
        "# SEM Pilot Analysis Summary",
        "",
        f"- Participants: {readiness['n_participants']}",
        f"- SEM-eligible participants: {readiness['n_sem_eligible_participants']} ({readiness['sem_eligible_participant_rate']:.1%})",
        f"- Ineligible participants: {readiness['ineligible_participants']}",
        f"- Task-level rows: {readiness['n_task_rows']}",
        f"- Complete task-row rate: {readiness['complete_task_row_rate']:.1%}",
        f"- SEM status: `{readiness['minimum_sem_status']}`",
        f"- Recommended next sample target: {readiness['recommended_next_sample_target']}",
        "",
        "## Condition Counts",
        "",
    ]
    for condition, count in readiness["condition_counts"].items():
        lines.append(f"- {condition}: {count}")
    lines.extend(["", "## Eligibility Issues", ""])
    if readiness.get("ineligible_reasons"):
        for reason, count in readiness["ineligible_reasons"].items():
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- No eligibility exclusions detected.")
    lines.extend(["", "## Scale Reliability", ""])
    for _, row in reliability.iterrows():
        alpha = row.get("cronbach_alpha")
        alpha_text = "NA" if pd.isna(alpha) else f"{alpha:.3f}"
        lines.append(f"- {row['construct']}: alpha={alpha_text}, complete n={int(row['n_complete'])}")
    lines.extend(["", "## Path Model Notes", ""])
    if paths.empty:
        lines.append("- Path coefficients were not estimated.")
    else:
        model_rows = paths[paths["predictor"] != "__model__"] if "predictor" in paths.columns else paths
        lines.append(f"- Estimated coefficient rows: {len(model_rows)}")
        lines.append("- See `path_coefficients.csv` for cluster-robust or HC3 standard errors.")
    lines.extend(["", "## Planned Contrasts", ""])
    for contrast in readiness.get("planned_contrasts", []):
        lines.append(f"- {contrast['name']}: {contrast['rationale']}")
    lines.extend(["", "## Caveats", ""])
    for note in readiness["notes"]:
        lines.append(f"- {note}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Fukui nudge pilot SEM precheck suite.")
    parser.add_argument("--input", required=True, type=Path, help="CSV or JSON export from local app or Supabase.")
    parser.add_argument("--output-dir", default=Path("experiments/sem_suite/output"), type=Path)
    parser.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = run_analysis(args.input, args.output_dir, args.config)
    print(
        f"Wrote SEM outputs to {args.output_dir} "
        f"({outputs.readiness['n_participants']} participants, {outputs.readiness['n_task_rows']} task rows)"
    )


if __name__ == "__main__":
    main()
