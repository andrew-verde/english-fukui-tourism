#!/usr/bin/env python3
"""causal_robustness.py — Falsification tests for the Fukui municipal SCM causal arm.

The primary causal-arm summary (build_causal_arm_summary.py) reports an
in-space placebo p-value on the POST-MEAN gap. For a transient effect (a large
opening surge that fades to ~0 within a year) the post-mean statistic averages
the spike away, so it understates the causal claim. This script derives the
falsification tests whose target quantity matches the effect's shape:

  1. In-space placebo on the OPENING WINDOW (Mar-Apr 2024): fit every donor
     municipality as-if-treated, build the null distribution of opening-window
     gaps, and locate each treated Fukui municipality in that null. One-sided
     (surge is directional: Shinkansen -> increase) and two-sided reported.
  2. In-time (backdated) placebo: move the event 12 months earlier (2023-03)
     using only genuinely pre-event data; a real 2024 effect should leave the
     backdated opening window null.
  3. Leave-one-out donor sensitivity for Fukui City: drop each positive-weight
     donor and refit, reporting the range of the opening surge.

Deterministic (Frank-Wolfe SCM, no RNG). Pure function of the pinned panel
fetched by build_causal_arm_summary.fetch_panel(). Writes CSVs + metrics.json
to output/national_stats/causal_robustness/.
"""
import argparse
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_causal_arm_summary import (  # noqa: E402
    fetch_panel, fw_scm_sparse, EVENT_YM, HOKURIKU_PREFS, EN_NAMES, GOOD_FIT_RMSPE,
)

OUT_DIR = ROOT / "output" / "national_stats" / "causal_robustness"
INTIME_EVENT_YM = 202303  # backdated placebo: one year before the real event
RMSPE_FIT_MULT = 5.0      # placebo restriction: drop donors with pre_rmspe > 5x treated


def _panel_matrices():
    raw = fetch_panel()
    raw["ym"] = raw["年"] * 100 + raw["月"]
    wide = raw.pivot_table(index="地域コード", columns="ym", values="人数", aggfunc="sum")
    meta = raw.groupby("地域コード").agg(pref=("都道府県コード", "first")).reset_index()
    pref_of = dict(zip(meta["地域コード"], meta["pref"]))
    full = wide.dropna(axis=0, how="any").copy()
    codes = full.index.to_numpy()
    pref_arr = np.array([pref_of[c] for c in codes])
    donor_codes = codes[~np.isin(pref_arr, HOKURIKU_PREFS)]
    months = sorted(raw["ym"].unique())
    fukui = [c for c in full.index if pref_of[c] == 18]
    return full, donor_codes, months, fukui


def _placebo_gaps(full, donor_codes, months, event_ym, pre_cap=None):
    """In-space placebo gaps for every donor, fit on the given event's pre-window."""
    pre_idx = [i for i, m in enumerate(months) if m < event_ym]
    if pre_cap is not None:
        pre_idx = pre_idx[-pre_cap:] if pre_cap < len(pre_idx) else pre_idx
    pre_labels = [months[i] for i in pre_idx]
    y_pre_don = np.log(full.loc[donor_codes, pre_labels].to_numpy(float))
    y_all_don = np.log(full.loc[donor_codes, months].to_numpy(float))
    gaps = np.zeros((len(donor_codes), len(months)))
    for k in range(len(donor_codes)):
        mask = np.ones(len(donor_codes), bool)
        mask[k] = False
        wk = fw_scm_sparse(y_pre_don[mask].T, y_pre_don[k], iters=400)
        gaps[k] = y_all_don[k] - wk @ y_all_don[mask]
    return gaps, pre_idx, y_pre_don, y_all_don


def _inspace(full, donor_codes, months, fukui):
    pre_idx = [i for i, m in enumerate(months) if m < EVENT_YM]
    post_idx = [i for i, m in enumerate(months) if m >= EVENT_YM]
    open_idx = post_idx[:2]  # Mar-Apr 2024
    gaps, _, y_pre_don, y_all_don = _placebo_gaps(full, donor_codes, months, EVENT_YM)
    pl_pre_rmspe = np.sqrt((gaps[:, pre_idx] ** 2).mean(axis=1))
    pl_open = gaps[:, open_idx].mean(axis=1)
    pl_meangap = gaps[:, post_idx].mean(axis=1)

    rows, dist_rows = [], []
    for code in fukui:
        y_all = np.log(full.loc[code, months].to_numpy(float))
        wk = fw_scm_sparse(y_pre_don.T, y_all[pre_idx], iters=1000)
        gap = y_all - wk @ y_all_don
        pre_r = np.sqrt((gap[pre_idx] ** 2).mean())
        open_spike = gap[open_idx].mean()
        mean_gap = gap[post_idx].mean()
        keep = pl_pre_rmspe <= RMSPE_FIT_MULT * pre_r
        p_open_1s = (1 + np.sum(pl_open[keep] >= open_spike)) / (1 + keep.sum())
        p_open_2s = (1 + np.sum(np.abs(pl_open[keep]) >= abs(open_spike))) / (1 + keep.sum())
        p_mean_2s = (1 + np.sum(np.abs(pl_meangap[keep]) >= abs(mean_gap))) / (1 + keep.sum())
        rows.append(dict(
            area_code=int(code), en=EN_NAMES.get(code, str(code)),
            pre_rmspe=pre_r, good_fit=bool(pre_r <= GOOD_FIT_RMSPE),
            open_spike_log=open_spike, open_pct=100 * (np.exp(open_spike) - 1),
            post_mean_gap_log=mean_gap,
            p_open_1s=p_open_1s, p_open_2s=p_open_2s, p_meangap_2s=p_mean_2s,
            n_placebos_kept=int(keep.sum()),
        ))
    # null distribution of opening-window placebo gaps (donor-level), for plotting
    for code, pr, og in zip(donor_codes, pl_pre_rmspe, pl_open):
        dist_rows.append(dict(area_code=int(code), pre_rmspe=float(pr),
                              open_gap_log=float(og),
                              open_pct=float(100 * (np.exp(og) - 1))))
    inspace = pd.DataFrame(rows).sort_values("open_pct", ascending=False).reset_index(drop=True)
    dist = pd.DataFrame(dist_rows)
    return inspace, dist


def _intime(full, donor_codes, months, fukui):
    """Backdated placebo: fake 2023-03 event; opening window 2023-03..04 should be null."""
    pre_idx = [i for i, m in enumerate(months) if m < INTIME_EVENT_YM]
    fake_post = [i for i, m in enumerate(months) if INTIME_EVENT_YM <= m < EVENT_YM]
    open_idx = fake_post[:2]
    pre_labels = [months[i] for i in pre_idx]
    y_pre_don = np.log(full.loc[donor_codes, pre_labels].to_numpy(float))
    y_all_don = np.log(full.loc[donor_codes, months].to_numpy(float))
    # placebo null on backdated opening window
    gaps, _, _, _ = _placebo_gaps(full, donor_codes, months, INTIME_EVENT_YM)
    pl_pre_rmspe = np.sqrt((gaps[:, pre_idx] ** 2).mean(axis=1))
    pl_open = gaps[:, open_idx].mean(axis=1)
    rows = []
    for code in fukui:
        y_all = np.log(full.loc[code, months].to_numpy(float))
        wk = fw_scm_sparse(y_pre_don.T, y_all[pre_idx], iters=1000)
        gap = y_all - wk @ y_all_don
        pre_r = np.sqrt((gap[pre_idx] ** 2).mean())
        fake_open = gap[open_idx].mean()
        keep = pl_pre_rmspe <= RMSPE_FIT_MULT * pre_r
        p_open_1s = (1 + np.sum(pl_open[keep] >= fake_open)) / (1 + keep.sum())
        rows.append(dict(
            area_code=int(code), en=EN_NAMES.get(code, str(code)),
            pre_rmspe=pre_r, backdated_open_spike_log=fake_open,
            backdated_open_pct=100 * (np.exp(fake_open) - 1),
            p_backdated_open_1s=p_open_1s, n_placebos_kept=int(keep.sum()),
        ))
    return pd.DataFrame(rows).sort_values("backdated_open_pct", ascending=False).reset_index(drop=True)


def _leave_one_out(full, donor_codes, months, target_code=18201):
    pre_idx = [i for i, m in enumerate(months) if m < EVENT_YM]
    open_idx = [i for i, m in enumerate(months) if m >= EVENT_YM][:2]
    y_pre_don = np.log(full.loc[donor_codes, [months[i] for i in pre_idx]].to_numpy(float))
    y_all_don = np.log(full.loc[donor_codes, months].to_numpy(float))
    y_all = np.log(full.loc[target_code, months].to_numpy(float))
    w = fw_scm_sparse(y_pre_don.T, y_all[pre_idx], iters=1000)
    gap = y_all - w @ y_all_don
    base_open = gap[open_idx].mean()
    pos = np.where(w > 1e-6)[0]
    rows = [dict(dropped_area_code="(none: baseline)", dropped_weight=float("nan"),
                 open_spike_log=base_open, open_pct=100 * (np.exp(base_open) - 1))]
    for j in pos:
        mask = np.ones(len(donor_codes), bool)
        mask[j] = False
        wj = fw_scm_sparse(y_pre_don[mask].T, y_all[pre_idx], iters=1000)
        gj = y_all - wj @ y_all_don[mask]
        oj = gj[open_idx].mean()
        rows.append(dict(dropped_area_code=int(donor_codes[j]), dropped_weight=float(w[j]),
                         open_spike_log=oj, open_pct=100 * (np.exp(oj) - 1)))
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    full, donor_codes, months, fukui = _panel_matrices()
    inspace, dist = _inspace(full, donor_codes, months, fukui)
    intime = _intime(full, donor_codes, months, fukui)
    loo = _leave_one_out(full, donor_codes, months)

    inspace.to_csv(out / "inspace_placebos.csv", index=False)
    dist.to_csv(out / "placebo_open_distribution.csv", index=False)
    intime.to_csv(out / "intime_placebo.csv", index=False)
    loo.to_csv(out / "leave_one_out_fukui_city.csv", index=False)

    fc = inspace[inspace["area_code"] == 18201].iloc[0]
    metrics = {
        "n_donors": int(len(donor_codes)),
        "event_ym": EVENT_YM,
        "intime_event_ym": INTIME_EVENT_YM,
        "opening_window": "2024-03..2024-04 (first two post months)",
        "fukui_city": {
            "open_pct": float(fc["open_pct"]),
            "pre_rmspe": float(fc["pre_rmspe"]),
            "p_open_1s": float(fc["p_open_1s"]),
            "p_open_2s": float(fc["p_open_2s"]),
            "p_meangap_2s": float(fc["p_meangap_2s"]),
            "n_placebos_kept": int(fc["n_placebos_kept"]),
        },
        "sig_open_1s_goodfit": inspace[(inspace["p_open_1s"] < 0.10) & inspace["good_fit"]]["en"].tolist(),
        "leave_one_out_open_pct_range": [float(loo["open_pct"].min()), float(loo["open_pct"].max())],
        "intime_max_backdated_open_pct": float(intime["backdated_open_pct"].abs().max()),
        "intime_fukui_city_p_1s": float(intime[intime["area_code"] == 18201]["p_backdated_open_1s"].iloc[0]),
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"wrote 4 CSVs + metrics.json to {out}")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
