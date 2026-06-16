#!/usr/bin/env python3
"""
Build the static data payload for the friction scenario simulator.

This is intentionally modest: it translates finalized SEM/nudge-ranking
artifacts into scenario parameters, then appends cited public-source context.
It does not estimate visitor counts, revenue, or opportunity-gap closure.

Reads:
  output/sem/sem_stage1_results.csv
  output/sem/nudge_priority_ranking.csv
  config/official_fukui_sources.yaml

Writes:
  experiments/friction-simulator/data/scenario_data.json
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
SEM_DIR = ROOT / "output" / "sem"
STAGE1_CSV = SEM_DIR / "sem_stage1_results.csv"
RANKING_CSV = SEM_DIR / "nudge_priority_ranking.csv"
SOURCES_YAML = ROOT / "config" / "official_fukui_sources.yaml"
OUT_JSON = ROOT / "experiments" / "friction-simulator" / "data" / "scenario_data.json"


def _required_float(df: pd.DataFrame, mask: pd.Series, column: str, label: str) -> float:
    values = pd.to_numeric(df.loc[mask, column], errors="coerce").dropna()
    if values.empty:
        raise ValueError(f"Missing required SEM value: {label}")
    return float(values.iloc[0])


def _clean_number(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, float):
        return round(value, 12)
    return value


def _load_sem_summary() -> dict[str, Any]:
    if not STAGE1_CSV.exists():
        raise FileNotFoundError(f"Missing {STAGE1_CSV}; run make sem-ftas first.")
    if not RANKING_CSV.exists():
        raise FileNotFoundError(f"Missing {RANKING_CSV}; run make nudge-ranking first.")

    stage1 = pd.read_csv(STAGE1_CSV)
    ranking = pd.read_csv(RANKING_CSV)

    friction_to_satisfaction = _required_float(
        stage1,
        (stage1["op"] == "~")
        & (stage1["lval"] == "SATISFACTION")
        & (stage1["rval"] == "friction"),
        "Est. Std",
        "friction -> SATISFACTION",
    )
    satisfaction_to_intention = _required_float(
        stage1,
        (stage1["op"] == "~")
        & (stage1["lval"] == "INTENTION")
        & (stage1["rval"] == "SATISFACTION"),
        "Est. Std",
        "SATISFACTION -> INTENTION",
    )
    direct_friction_to_intention = _required_float(
        stage1,
        (stage1["op"] == "~")
        & (stage1["lval"] == "INTENTION")
        & (stage1["rval"] == "friction"),
        "Est. Std",
        "friction -> INTENTION",
    )

    required_columns = {
        "friction_code",
        "friction_label",
        "sem_path_to_satisfaction_std",
        "p_value",
        "journey_stage",
        "nudge_type",
        "example_intervention",
        "n_reporters_tagged",
        "prevalence_among_reporters",
        "priority_score",
    }
    missing = required_columns - set(ranking.columns)
    if missing:
        raise ValueError(f"{RANKING_CSV} is missing columns: {sorted(missing)}")

    friction_codes = []
    for _, row in ranking.sort_values("rank").iterrows():
        path = float(row["sem_path_to_satisfaction_std"])
        prevalence = float(row["prevalence_among_reporters"])
        recoverable_intention_ceiling = max(-path, 0.0) * prevalence * abs(satisfaction_to_intention)
        friction_codes.append(
            {
                "code": row["friction_code"],
                "label": row["friction_label"],
                "journey_stage": row["journey_stage"],
                "nudge_type": row["nudge_type"],
                "example_intervention": row["example_intervention"],
                "sem_path_to_satisfaction_std": _clean_number(path),
                "p_value": _clean_number(float(row["p_value"])),
                "n_reporters_tagged": int(row["n_reporters_tagged"]),
                "prevalence_among_reporters": _clean_number(prevalence),
                "priority_score": _clean_number(float(row["priority_score"])),
                "recoverable_intention_ceiling": _clean_number(recoverable_intention_ceiling),
            }
        )

    return {
        "stage1": {
            "friction_to_satisfaction_std": _clean_number(friction_to_satisfaction),
            "satisfaction_to_intention_std": _clean_number(satisfaction_to_intention),
            "direct_friction_to_intention_std": _clean_number(direct_friction_to_intention),
        },
        "friction_codes": friction_codes,
    }


def _public_sources() -> list[dict[str, str]]:
    config = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    sources = []
    seen: set[tuple[str, str]] = set()
    for source in config["sources"].values():
        key = (source["upstream_repo"], source["description"])
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "name": source["description"],
                "repo": source["upstream_repo"],
                "url": source["url"],
                "role": "Public context source; use for segmentation, baselines, or cited descriptive context.",
            }
        )
    sources.append(
        {
            "name": "Hokuriku Tourism AI Governance Framework",
            "repo": "https://github.com/amilkh/hokuriku-tourism-ai-governance",
            "url": "https://github.com/amilkh/hokuriku-tourism-ai-governance",
            "role": (
                "Cited contextual source for weather, route-intent, people-flow, and governance framing; "
                "not used here to estimate opportunity-gap closure."
            ),
        }
    )
    return sources


def build_payload() -> dict[str, Any]:
    sem = _load_sem_summary()
    return {
        "schema_version": 1,
        "generated_on": date.today().isoformat(),
        "title": "Fukui friction nudge scenario simulator",
        "status": "framework_seeded_from_current_sem_outputs",
        "interpretation": {
            "primary_unit": "standardized latent visit-intention units",
            "claim_boundary": (
                "Scenario values are sensitivity calculations from SEM paths and assumed nudge effectiveness. "
                "They are not causal impact, visitor-volume, revenue, or opportunity-gap forecasts."
            ),
            "default_effectiveness": 0.25,
            "default_reach": 0.5,
            "formula": (
                "estimated_intention_shift = max(-friction_code_path_to_satisfaction, 0) "
                "* prevalence_among_reporters * satisfaction_to_intention_path "
                "* assumed_effectiveness * assumed_reach"
            ),
        },
        "sem": sem,
        "public_sources": _public_sources(),
        "refresh": {
            "command": "make friction-simulator-data",
            "upstream_commands": ["make sem-ftas", "make nudge-ranking"],
        },
    }


def main() -> int:
    payload = build_payload()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
