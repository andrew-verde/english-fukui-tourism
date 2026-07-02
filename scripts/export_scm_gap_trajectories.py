#!/usr/bin/env python3
"""Export per-target synthetic-control gap trajectories from the local panel."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_causal_arm_summary import (  # noqa: E402
    EN_NAMES,
    EVENT_YM,
    HOKURIKU_PREFS,
    fw_scm_sparse,
)

PANEL_CSV = ROOT / "output" / "national_stats" / "japan_kanko_stat_panel.csv"
REFERENCE_CSV = ROOT / "data" / "causal" / "fukui_municipalities_scm.csv"
OUT_CSV = (
    ROOT
    / "output"
    / "national_stats"
    / "causal_robustness"
    / "target_gap_trajectories.csv"
)


def build_trajectories() -> pd.DataFrame:
    """Fit each Fukui target and return its full monthly SCM trajectory."""
    raw = pd.read_csv(PANEL_CSV)

    wide = raw.pivot_table(
        index="地域コード", columns="ym", values="人数", aggfunc="sum"
    )
    meta = raw.groupby("地域コード").agg(
        pref=("都道府県コード", "first"),
        name=("地域名称", lambda s: s.mode().iloc[0]),
    ).reset_index()
    pref_of = dict(zip(meta["地域コード"], meta["pref"]))

    full = wide.dropna(axis=0, how="any").copy()
    codes = full.index.to_numpy()
    pref_arr = np.array([pref_of[c] for c in codes])
    donor_codes = codes[~np.isin(pref_arr, HOKURIKU_PREFS)]

    months = sorted(raw["ym"].unique())
    pre_idx = [i for i, month in enumerate(months) if month < EVENT_YM]
    pre_labels = [months[i] for i in pre_idx]

    y_pre_don = np.log(full.loc[donor_codes, pre_labels].to_numpy(float))
    y_all_don = np.log(full.loc[donor_codes, months].to_numpy(float))

    rows = []
    fukui_codes = [code for code in full.index if pref_of[code] == 18]
    for code in fukui_codes:
        actual = np.log(full.loc[code, months].to_numpy(float))
        weights = fw_scm_sparse(
            y_pre_don.T, actual[pre_idx], iters=1000
        )
        synthetic = weights @ y_all_don
        gap = actual - synthetic
        rows.extend(
            {
                "area_code": int(code),
                "en": EN_NAMES[code],
                "ym": int(month),
                "actual_log": actual[i],
                "synthetic_log": synthetic[i],
                "gap_log": gap[i],
            }
            for i, month in enumerate(months)
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["area_code", "ym"])
        .reset_index(drop=True)
    )


def assert_matches_reference(trajectories: pd.DataFrame) -> None:
    """Check trajectory-derived opening and sustained effects against Feed A."""
    effects = (
        trajectories.groupby("area_code")
        .apply(
            lambda target: pd.Series(
                {
                    "open_pct": 100
                    * (
                        np.exp(
                            target.loc[
                                target["ym"] >= EVENT_YM, "gap_log"
                            ].iloc[:2].mean()
                        )
                        - 1
                    ),
                    "sust_pct": 100
                    * (
                        np.exp(
                            target.loc[
                                target["ym"] // 100 == 2025, "gap_log"
                            ].mean()
                        )
                        - 1
                    ),
                }
            )
        )
        .reset_index()
    )
    reference = pd.read_csv(REFERENCE_CSV)[
        ["area_code", "open_pct", "sust_pct"]
    ]
    checked = effects.merge(
        reference,
        on="area_code",
        how="outer",
        validate="one_to_one",
        suffixes=("_actual", "_reference"),
        indicator=True,
    )
    if not (checked["_merge"] == "both").all():
        raise AssertionError("Feed A area-code mismatch")
    for metric in ("open_pct", "sust_pct"):
        if not np.allclose(
            checked[f"{metric}_actual"],
            checked[f"{metric}_reference"],
            atol=1e-4,
            rtol=0,
        ):
            delta = np.max(
                np.abs(
                    checked[f"{metric}_actual"]
                    - checked[f"{metric}_reference"]
                )
            )
            raise AssertionError(
                f"Feed A {metric} drift exceeds atol=0.0001: "
                f"max delta={delta}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    trajectories = build_trajectories()
    assert_matches_reference(trajectories)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    trajectories.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV.relative_to(ROOT)} ({len(trajectories)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
