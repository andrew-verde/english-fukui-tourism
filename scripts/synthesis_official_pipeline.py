#!/usr/bin/env python3
"""Write concise summaries for official-survey statistical results."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL_DIR = ROOT / "output" / "official_fukui"
RESULTS_JSON = OFFICIAL_DIR / "statistical_results_official.json"
SUMMARY_MD = OFFICIAL_DIR / "statistical_summary_official.md"
THESIS_ASSESSMENT_MD = OFFICIAL_DIR / "thesis_readiness_assessment.md"


def _fmt_p(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "NA"
    return "<0.001" if number < 0.001 else f"{number:.3f}"


def _result_lines(result: dict) -> list[str]:
    name = result.get("name", "unnamed test")
    n = result.get("n", 0)
    details = result.get("details", {})
    lines = [f"### `{name}`", "", f"- N: {n:,}" if isinstance(n, int) else f"- N: {n}"]
    for key in ("test", "statistic", "p_value", "p_value_bh", "effect_size", "interpretation"):
        if key not in details:
            continue
        value = details[key]
        if key.startswith("p_value"):
            value = _fmt_p(value)
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    lines.append("")
    return lines


def main() -> int:
    payload = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    results = payload.get("results", [])
    audit = payload.get("audit", {})

    summary = [
        "# Official Fukui Tourism Survey Statistical Summary",
        "",
        "All results use official Fukui and Ishikawa survey data. Units,",
        "deduplication rules, and denominators are defined by",
        "`scripts/statistical_validation_official.py`.",
        "",
        f"- Generated from `{RESULTS_JSON.relative_to(ROOT)}`",
        f"- Statistical results: {len(results)}",
        f"- Audit fields: {len(audit)}",
        "",
        "## Results",
        "",
    ]
    for result in results:
        summary.extend(_result_lines(result))
    SUMMARY_MD.write_text("\n".join(summary), encoding="utf-8")

    assessment = [
        "# Thesis Readiness Assessment",
        "",
        "## Evidence base",
        "",
        "- Main inferential evidence: official Fukui FTAS and Ishikawa survey data.",
        "- Impact analysis: merged Hokuriku survey event study around the March 2024 Shinkansen extension.",
        "- Mechanism analysis: two-stage SEM on deduplicated FTAS respondents.",
        "- Intervention ranking: SEM path strength combined with official-survey prevalence.",
        "",
        "## Required interpretation",
        "",
        "- Preserve respondent-level denominators and documented deduplication.",
        "- Treat keyword friction tags as measured indicators, not ground truth.",
        "- Report effect sizes and uncertainty alongside p-values.",
        "- Keep exploratory Chinese social-media outputs outside thesis inference.",
        "",
        "Reproduce with `make reproduce-submission`.",
        "",
    ]
    THESIS_ASSESSMENT_MD.write_text("\n".join(assessment), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
