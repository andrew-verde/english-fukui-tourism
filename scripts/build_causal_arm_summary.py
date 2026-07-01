#!/usr/bin/env python3
"""Regenerate the causal-arm per-municipality synthetic-control summary (Feed A).

Fetches the code4fukui japan-kanko-stat monthly city visitor panel at a
commit-pinned revision and fits a per-municipality synthetic control against a
donor pool that excludes the Hokuriku-affected prefectures (Niigata 15, Toyama
16, Ishikawa 17, Fukui 18). Emits the 17-row Fukui summary consumed by the
synthesis arm (scripts/synthesis_friction_causal.py) as Feed A.

The Frank-Wolfe SCM solver uses no RNG and the data source is pinned by commit
SHA. Regeneration is deterministic up to BLAS-level floating-point noise and is
checked numerically against the committed, byte-stable fixture.

Outputs
-------
data/causal/fukui_municipalities_scm.csv   (17 rows; Feed A)
"""
from __future__ import annotations

import argparse
import io
import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "causal"
OUT_CSV = OUT_DIR / "fukui_municipalities_scm.csv"

# code4fukui japan-kanko-stat, pinned commit (monthly city visitor panel).
DATA_COMMIT = "dfb906975b63adcaef20a3e7a35f2a10ab22ada5"
DATA_BASE = f"https://raw.githubusercontent.com/code4fukui/japan-kanko-stat/{DATA_COMMIT}/data"

EVENT_YM = 202403  # Hokuriku Shinkansen Fukui extension, 2024-03.
HOKURIKU_PREFS = (15, 16, 17, 18)  # Niigata, Toyama, Ishikawa, Fukui.
GOOD_FIT_RMSPE = 0.15

# Documented checksum of the committed, byte-stable Feed A fixture. Tests check
# this exact value; freshly computed values use the numeric contract below.
EXPECTED_SHA256 = "ff6cd1afecb0ec1175434cba0ab9964511fe9167ef57166c50e8ba713f84d953"

NUMERIC_COLUMNS = [
    "pre_rmspe", "open_spike_log", "sustained_2025_log",
    "post_mean_gap_log", "open_pct", "sust_pct", "rmspe_ratio",
    "p_meangap", "p_ratio",
]
EXACT_COLUMNS = ["area_code", "en", "name", "good_fit"]
NUMERIC_ATOL = 1e-6

EN_NAMES = {
    18201: "Fukui City", 18202: "Tsuruga", 18204: "Obama", 18205: "Ono",
    18206: "Katsuyama", 18207: "Sabae", 18208: "Awara", 18209: "Echizen City",
    18210: "Sakai", 18322: "Eiheiji", 18382: "Ikeda", 18404: "Minami-Echizen",
    18423: "Echizen Town", 18442: "Mihama", 18481: "Takahama", 18483: "Oi",
    18501: "Wakasa",
}


def fetch_panel() -> pd.DataFrame:
    """Concatenate the pinned 2021-2025 city CSVs into one long panel."""
    frames = []
    for year in range(2021, 2026):
        resp = requests.get(f"{DATA_BASE}/city{year}.csv", timeout=60)
        resp.raise_for_status()
        frames.append(pd.read_csv(io.StringIO(resp.text)))
    return pd.concat(frames, ignore_index=True)


def fw_scm_sparse(A: np.ndarray, b: np.ndarray, iters: int = 1000,
                  tol: float = 1e-9) -> np.ndarray:
    """Frank-Wolfe synthetic-control weights on the unit simplex.

    Minimises || A w - b ||^2 with w >= 0, sum(w) = 1. Deterministic: the
    initial vertex is the single donor with lowest MSE against the target,
    then convex steps toward the min-gradient vertex. No RNG.
    """
    n = A.shape[1]
    err = np.array([np.mean((A[:, j] - b) ** 2) for j in range(n)])
    w = np.zeros(n)
    w[np.argmin(err)] = 1.0
    r = A @ w - b
    for _ in range(iters):
        grad = A.T @ r
        j = np.argmin(grad)
        direction = A[:, j] - A @ w
        denom = direction @ direction
        if denom < tol:
            break
        gamma = np.clip(-(r @ direction) / denom, 0.0, 1.0)
        if gamma < tol:
            break
        w *= (1 - gamma)
        w[j] += gamma
        r = r + gamma * direction
    return w


def build_summary() -> pd.DataFrame:
    raw = fetch_panel()
    raw["ym"] = raw["年"] * 100 + raw["月"]

    wide = raw.pivot_table(index="地域コード", columns="ym", values="人数",
                           aggfunc="sum")
    meta = raw.groupby("地域コード").agg(
        pref=("都道府県コード", "first"),
        name=("地域名称", lambda s: s.mode().iloc[0]),
    ).reset_index()
    pref_of = dict(zip(meta["地域コード"], meta["pref"]))
    name_of = dict(zip(meta["地域コード"], meta["name"]))

    full = wide.dropna(axis=0, how="any").copy()
    codes = full.index.to_numpy()
    pref_arr = np.array([pref_of[c] for c in codes])
    donor_codes = codes[~np.isin(pref_arr, HOKURIKU_PREFS)]

    months = sorted(raw["ym"].unique())
    pre_idx = [i for i, m in enumerate(months) if m < EVENT_YM]
    post_idx = [i for i, m in enumerate(months) if m >= EVENT_YM]
    pre_labels = [months[i] for i in pre_idx]

    y_pre_don = np.log(full.loc[donor_codes, pre_labels].to_numpy(float))
    y_all_don = np.log(full.loc[donor_codes, months].to_numpy(float))

    # Placebo (in-space) inference: fit each donor as if treated.
    placebo_gaps = np.zeros((len(donor_codes), len(months)))
    for k in range(len(donor_codes)):
        mask = np.ones(len(donor_codes), bool)
        mask[k] = False
        wk = fw_scm_sparse(y_pre_don[mask].T, y_pre_don[k], iters=400)
        placebo_gaps[k] = y_all_don[k] - wk @ y_all_don[mask]
    pl_meangap = placebo_gaps[:, post_idx].mean(axis=1)
    pl_pre_rmspe = np.sqrt((placebo_gaps[:, pre_idx] ** 2).mean(axis=1))
    pl_ratio = (np.sqrt((placebo_gaps[:, post_idx] ** 2).mean(axis=1))
                / pl_pre_rmspe)

    fukui_codes = [c for c in full.index if pref_of[c] == 18]
    rows = []
    for code in fukui_codes:
        y_all = np.log(full.loc[code, months].to_numpy(float))
        wk = fw_scm_sparse(y_pre_don.T, y_all[pre_idx], iters=1000)
        gap = y_all - wk @ y_all_don

        pre_r = np.sqrt((gap[pre_idx] ** 2).mean())
        post_r = np.sqrt((gap[post_idx] ** 2).mean())
        ratio = post_r / pre_r
        mean_gap = gap[post_idx].mean()
        open_spike = gap[post_idx[:2]].mean()
        y2025 = [i for i in post_idx if months[i] // 100 == 2025]
        sustained = gap[y2025].mean()

        p_mean = (1 + np.sum(np.abs(pl_meangap) >= abs(mean_gap))) / (1 + len(pl_meangap))
        keep = pl_pre_rmspe <= 5 * pre_r
        p_ratio = (1 + np.sum(pl_ratio[keep] >= ratio)) / (1 + keep.sum())

        rows.append(dict(
            area_code=code, name=name_of[code], pre_rmspe=pre_r,
            open_spike_log=open_spike, sustained_2025_log=sustained,
            post_mean_gap_log=mean_gap, rmspe_ratio=ratio,
            p_meangap=p_mean, p_ratio=p_ratio,
        ))

    mun = (pd.DataFrame(rows)
           .sort_values("open_spike_log", ascending=False)
           .reset_index(drop=True))
    mun["en"] = mun["area_code"].map(EN_NAMES)
    mun["open_pct"] = 100 * (np.exp(mun["open_spike_log"]) - 1)
    mun["sust_pct"] = 100 * (np.exp(mun["sustained_2025_log"]) - 1)
    mun["good_fit"] = mun["pre_rmspe"] <= GOOD_FIT_RMSPE

    return mun[[
        "area_code", "en", "name", "pre_rmspe", "good_fit", "open_spike_log",
        "sustained_2025_log", "post_mean_gap_log", "open_pct", "sust_pct",
        "rmspe_ratio", "p_meangap", "p_ratio",
    ]]


def assert_matches_reference(summary: pd.DataFrame, reference: pd.DataFrame) -> None:
    """Enforce the numeric and regime-boundary contract for committed Feed A."""
    if len(summary) != len(reference):
        raise AssertionError(
            f"Feed A row-count drift: got {len(summary)}, expected {len(reference)}"
        )
    for column in EXACT_COLUMNS:
        if not summary[column].reset_index(drop=True).equals(
            reference[column].reset_index(drop=True)
        ):
            raise AssertionError(f"Feed A exact-column drift: {column}")
    if not np.allclose(
        summary[NUMERIC_COLUMNS].to_numpy(float),
        reference[NUMERIC_COLUMNS].to_numpy(float),
        atol=NUMERIC_ATOL,
        rtol=0,
    ):
        delta = np.max(np.abs(
            summary[NUMERIC_COLUMNS].to_numpy(float)
            - reference[NUMERIC_COLUMNS].to_numpy(float)
        ))
        raise AssertionError(
            f"Feed A numeric drift exceeds atol={NUMERIC_ATOL}: max delta={delta}"
        )
    for decision, column, threshold in (
        ("open_pct > 5", "open_pct", 5),
        ("sust_pct >= 0", "sust_pct", 0),
    ):
        if not np.array_equal(
            summary[column].to_numpy() > threshold
            if decision == "open_pct > 5"
            else summary[column].to_numpy() >= threshold,
            reference[column].to_numpy() > threshold
            if decision == "open_pct > 5"
            else reference[column].to_numpy() >= threshold,
        ):
            raise AssertionError(f"Feed A regime-boundary drift: {decision}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true",
        help="overwrite the committed fixture after its contract passes",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = build_summary()
    if OUT_CSV.exists():
        reference = pd.read_csv(OUT_CSV)
        assert_matches_reference(summary, reference)
        if not (args.force or os.environ.get("RUN_NETWORK_TESTS")):
            print(
                f"{OUT_CSV.relative_to(ROOT)} matches committed reference "
                f"within atol={NUMERIC_ATOL}; left unchanged"
            )
            return

    summary.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV.relative_to(ROOT)} ({len(summary)} rows)")


if __name__ == "__main__":
    main()
