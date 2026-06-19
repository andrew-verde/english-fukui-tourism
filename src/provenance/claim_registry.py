from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.provenance.gold_set import GoldSetStatus, get_gold_set_status


ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_CLAIM_FIELDS = {
    "claim_id",
    "title",
    "status",
    "evidence_layer",
    "unit_of_analysis",
    "population",
    "scope",
    "denominator",
    "method",
    "estimate",
    "source_artifacts",
    "reproduction_command",
    "caveats",
}


@dataclass(frozen=True)
class SourceArtifact:
    path: str
    sha256: str | None
    rows: int | None = None
    columns: list[str] | None = None


@dataclass(frozen=True)
class ClaimResult:
    claim_id: str
    title: str
    status: str
    evidence_layer: str
    unit_of_analysis: str
    population: str
    scope: str
    denominator: str
    method: str
    estimate: dict[str, Any]
    source_artifacts: list[SourceArtifact]
    reproduction_command: str
    caveats: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)
    interpretation: str = ""


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _describe_csv(path: Path) -> tuple[int | None, list[str] | None]:
    if not path.exists():
        return None, None
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        return sum(1 for _ in reader), header


def artifact(path: Path) -> SourceArtifact:
    rel = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
    rows = columns = None
    full = ROOT / rel
    if full.suffix == ".csv":
        rows, columns = _describe_csv(full)
    return SourceArtifact(path=rel, sha256=_sha256(full), rows=rows, columns=columns)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def _float(value: Any) -> float | None:
    try:
        if value in ("", "-", None):
            return None
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(out) else out


def _find_result(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for result in payload.get("results", []):
        if result.get("name") == name:
            return result
    raise KeyError(f"Missing result: {name}")


def _git_head() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _git_dirty() -> bool | None:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        return bool(status.strip())
    except (OSError, subprocess.SubprocessError):
        return None


def _status(tag_dependent: bool, gold_status: GoldSetStatus) -> str:
    if tag_dependent and not gold_status.complete:
        return "provisional_pending_gold_set"
    return "verified"


def build_claims(root: Path = ROOT) -> list[ClaimResult]:
    official_path = root / "output" / "official_fukui" / "statistical_results_official.json"
    did_path = root / "output" / "hokuriku_merged" / "did_thesis_estimates.csv"
    sem_stage1_path = root / "output" / "sem" / "sem_stage1_results.csv"
    sem_stage2_path = root / "output" / "sem" / "sem_stage2_results.csv"
    prevalence_path = root / "output" / "sem" / "sem_stage2_prevalence.csv"
    nudge_path = root / "output" / "sem" / "nudge_priority_ranking.csv"

    official = _read_json(official_path)
    did_rows = _read_csv_rows(did_path)
    stage1 = _read_csv_rows(sem_stage1_path)
    stage2 = _read_csv_rows(sem_stage2_path)
    nudge = _read_csv_rows(nudge_path)
    gold_status = get_gold_set_status(root)

    claims: list[ClaimResult] = []
    official_artifacts = [
        artifact(official_path),
        artifact(root / "scripts" / "statistical_validation_official.py"),
    ]

    audit = _find_result(official, "official_input_data_audit")
    dedup = official.get("method_notes", {}).get("respondent_dedup", {})
    claims.append(
        ClaimResult(
            claim_id="official_ftas_dedup_sample",
            title="FTAS inference uses first response per respondent",
            status="verified",
            evidence_layer="Official survey layer",
            unit_of_analysis="one survey respondent",
            population="Japanese survey respondents in Fukui FTAS",
            scope="Fukui FTAS rows after member-ID deduplication",
            denominator="deduplicated respondent rows",
            method="deterministic audit",
            estimate={
                "raw_rows": dedup.get("n_rows"),
                "deduplicated_rows": dedup.get("n_after_dedup"),
                "dropped_repeat_responses": dedup.get("n_dropped_repeat_responses"),
            },
            statistics={"audit_valid": audit.get("details", {}).get("valid")},
            source_artifacts=official_artifacts,
            reproduction_command="make stats-official",
            caveats=["Rows without respondent_id cannot be proven duplicates and are kept."],
            interpretation="Repeat submissions are not treated as independent respondents.",
        )
    )

    sat = _find_result(official, "official_friction_vs_satisfaction")
    full = sat["details"]["reported_inconvenience_full_sample"]["outcomes"]
    claims.append(
        ClaimResult(
            claim_id="reported_inconvenience_satisfaction_intention",
            title="Reported inconvenience is associated with lower satisfaction and NPS",
            status="verified",
            evidence_layer="Official survey layer",
            unit_of_analysis="one survey respondent",
            population="Japanese survey respondents in Fukui FTAS",
            scope="Full deduplicated FTAS sample",
            denominator="all respondents with nonmissing outcome values",
            method="Mann-Whitney U tests by reported_inconvenience",
            estimate={
                "overall_satisfaction_mean_difference": full["overall_satisfaction_score"]["mean_difference"],
                "transport_satisfaction_mean_difference": full["transport_satisfaction_score"]["mean_difference"],
                "nps_mean_difference": full["nps"]["mean_difference"],
            },
            statistics={
                "overall_satisfaction_p": full["overall_satisfaction_score"]["p_value"],
                "transport_satisfaction_p": full["transport_satisfaction_score"]["p_value"],
                "nps_p": full["nps"]["p_value"],
                "overall_satisfaction_rank_biserial_r": full["overall_satisfaction_score"]["rank_biserial_r"],
                "nps_rank_biserial_r": full["nps"]["rank_biserial_r"],
            },
            source_artifacts=official_artifacts,
            reproduction_command="make stats-official",
            caveats=["Reported inconvenience is observational, not randomized."],
            interpretation="Closed-form inconvenience exposure is the primary friction measure free of free-text selection bias.",
        )
    )

    pref = _find_result(official, "official_prefecture_comparison")
    any_friction = pref["details"]["any_friction"]
    claims.append(
        ClaimResult(
            claim_id="official_fukui_ishikawa_text_writer_friction",
            title="Fukui/Ishikawa friction-code comparisons use text-writer denominator",
            status=_status(True, gold_status),
            evidence_layer="Official survey layer",
            unit_of_analysis="one survey respondent with free text",
            population="Japanese survey respondents in Fukui FTAS and Ishikawa official survey",
            scope="Fukui vs Ishikawa official survey comparison",
            denominator="respondents with non-empty friction_source_text",
            method="2x2 chi-square tests with BH correction across friction codes",
            estimate={
                "fukui_any_friction_rate": any_friction.get("rates", {}).get("Fukui"),
                "ishikawa_any_friction_rate": any_friction.get("rates", {}).get("Ishikawa"),
            },
            statistics={"p_value": any_friction.get("p_value"), "cramers_v": any_friction.get("cramers_v")},
            source_artifacts=official_artifacts,
            reproduction_command="make stats-official",
            caveats=[
                "Text-response rates differ by instrument; all-respondent friction rates are not comparable.",
                gold_status.caveat,
            ]
            if not gold_status.complete
            else ["Text-response rates differ by instrument; all-respondent friction rates are not comparable."],
            interpretation="Prefecture comparison is harmonized official-survey evidence, not identical-instrument evidence.",
        )
    )

    stage1_lookup = {(r["lval"], r["op"], r["rval"]): r for r in stage1}
    friction_to_sat = _float(stage1_lookup[("SATISFACTION", "~", "friction")]["Est. Std"])
    sat_to_intention = _float(stage1_lookup[("INTENTION", "~", "SATISFACTION")]["Est. Std"])
    friction_direct = _float(stage1_lookup[("INTENTION", "~", "friction")]["Est. Std"])
    indirect = friction_to_sat * sat_to_intention if friction_to_sat is not None and sat_to_intention is not None else None
    total = indirect + friction_direct if indirect is not None and friction_direct is not None else None
    mediated_share = abs(indirect / total) if indirect is not None and total else None
    sem_artifacts = [
        artifact(sem_stage1_path),
        artifact(root / "output" / "sem" / "sem_fit_indices.csv"),
        artifact(root / "scripts" / "sem_ftas.py"),
    ]
    claims.append(
        ClaimResult(
            claim_id="ftas_sem_friction_satisfaction_intention",
            title="FTAS SEM supports friction -> satisfaction -> intention mechanism",
            status="verified",
            evidence_layer="Official survey layer",
            unit_of_analysis="one deduplicated survey respondent",
            population="Japanese survey respondents in Fukui FTAS",
            scope="Stage 1 SEM on reported_inconvenience and satisfaction/intention indicators",
            denominator="deduplicated respondents with complete SEM indicators",
            method="structural equation model",
            estimate={
                "friction_to_satisfaction_std": friction_to_sat,
                "satisfaction_to_intention_std": sat_to_intention,
                "friction_to_intention_direct_std": friction_direct,
                "indirect_effect_std": indirect,
                "mediated_share_abs": mediated_share,
            },
            statistics={
                "friction_to_satisfaction_p": _float(stage1_lookup[("SATISFACTION", "~", "friction")]["p-value"]),
                "satisfaction_to_intention_p": _float(stage1_lookup[("INTENTION", "~", "SATISFACTION")]["p-value"]),
                "friction_direct_p": _float(stage1_lookup[("INTENTION", "~", "friction")]["p-value"]),
            },
            source_artifacts=sem_artifacts,
            reproduction_command="make sem-ftas",
            caveats=["SEM is observational; causal interpretation depends on modeling assumptions."],
            interpretation="Mechanism claim rests on official open data, not recruited pilot data.",
        )
    )

    top = nudge[0]
    claims.append(
        ClaimResult(
            claim_id="nudge_priority_transport_access",
            title="Transport/access is the top evidence-weighted nudge priority",
            status=_status(True, gold_status),
            evidence_layer="Official survey layer",
            unit_of_analysis="one friction reporter with free text",
            population="Japanese survey respondents in Fukui FTAS with reported inconvenience and free text",
            scope="SEM Stage 2 friction-code ranking",
            denominator="friction reporters with free text",
            method="priority_score = negative satisfaction path x prevalence x Stage 1 satisfaction->intention path",
            estimate={
                "top_friction_code": top.get("friction_code"),
                "priority_score": _float(top.get("priority_score")),
                "sem_path_to_satisfaction_std": _float(top.get("sem_path_to_satisfaction_std")),
                "prevalence_among_reporters": _float(top.get("prevalence_among_reporters")),
            },
            statistics={"p_value": _float(top.get("p_value"))},
            source_artifacts=[
                artifact(nudge_path),
                artifact(sem_stage2_path),
                artifact(prevalence_path),
                artifact(root / "scripts" / "rank_nudge_priorities.py"),
            ],
            reproduction_command="make sem-ftas nudge-ranking",
            caveats=[gold_status.caveat] if not gold_status.complete else [],
            interpretation="Ranking is a scenario ceiling for intervention design, not a measured nudge-effectiveness estimate.",
        )
    )

    def did_claim(outcome: str, claim_id: str, title: str) -> ClaimResult:
        baseline = next(r for r in did_rows if r["spec"] == "baseline" and r["outcome"] == outcome)
        robust = next(r for r in did_rows if r["spec"] == "composition_controls" and r["outcome"] == outcome)
        return ClaimResult(
            claim_id=claim_id,
            title=title,
            status="verified",
            evidence_layer="Official survey layer",
            unit_of_analysis="one survey respondent",
            population="Merged Hokuriku official survey respondents",
            scope="Fukui treated; Ishikawa/Toyama controls around 2024-03-16 Shinkansen shock",
            denominator="survey respondents with outcome in DiD model",
            method="difference-in-differences/event-study with clustered standard errors",
            estimate={
                "baseline_estimate": _float(baseline["estimate"]),
                "composition_controls_estimate": _float(robust["estimate"]),
                "ci_low": _float(baseline["ci_low"]),
                "ci_high": _float(baseline["ci_high"]),
            },
            statistics={
                "baseline_p_value": _float(baseline["p_value"]),
                "composition_controls_p_value": _float(robust["p_value"]),
                "n": int(float(baseline["n"])),
                "n_clusters": int(float(baseline["n_clusters"])),
            },
            source_artifacts=[
                artifact(did_path),
                artifact(root / "output" / "hokuriku_merged" / "did_event_study_coefficients.csv"),
                artifact(root / "scripts" / "hokuriku_did_event_study.py"),
            ],
            reproduction_command="make hokuriku-did-event-study",
            caveats=["Parallel-trends and shock-exogeneity assumptions must be argued in text."],
            interpretation="Causal friction-impact claim uses official survey comparison prefectures, not Google reviews.",
        )

    claims.append(
        did_claim(
            "nps",
            "hokuriku_did_nps",
            "Shinkansen shock raised Fukui NPS relative to control prefectures",
        )
    )
    claims.append(
        did_claim(
            "transport_satisfaction",
            "hokuriku_did_transport_satisfaction",
            "Shinkansen shock raised Fukui transport satisfaction relative to controls",
        )
    )

    return claims


def validate_claims(claims: list[ClaimResult]) -> None:
    ids = [claim.claim_id for claim in claims]
    duplicates = sorted({claim_id for claim_id in ids if ids.count(claim_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate claim_id values: {', '.join(duplicates)}")
    for claim in claims:
        payload = asdict(claim)
        missing = sorted(field for field in REQUIRED_CLAIM_FIELDS if not payload.get(field))
        if missing:
            raise ValueError(f"{claim.claim_id} missing required fields: {', '.join(missing)}")
        if not claim.source_artifacts:
            raise ValueError(f"{claim.claim_id} has no source artifacts")
        missing_hashes = [item.path for item in claim.source_artifacts if item.sha256 is None]
        if missing_hashes:
            raise ValueError(f"{claim.claim_id} references missing artifacts: {', '.join(missing_hashes)}")


def build_registry(root: Path = ROOT) -> dict[str, Any]:
    claims = build_claims(root)
    validate_claims(claims)
    gold_status = get_gold_set_status(root)
    gold_status_payload = asdict(gold_status)
    gold_status_payload["evaluation_csv"] = str(gold_status.evaluation_csv.relative_to(root))
    gold_status_payload["report_md"] = str(gold_status.report_md.relative_to(root))
    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "git_head": _git_head(),
        "git_dirty": _git_dirty(),
        "publication_ready": all(claim.status == "verified" for claim in claims) and gold_status.complete,
        "gold_set_status": gold_status_payload,
        "claims": [asdict(claim) for claim in claims],
    }


def write_markdown(registry: dict[str, Any]) -> str:
    lines = [
        "# Statistical Claim Registry",
        "",
        f"Generated: {registry['generated_at']}",
        f"Publication ready: {registry['publication_ready']}",
        f"Gold-set status: {registry['gold_set_status']['reason']}",
        "",
        "| Claim | Status | Unit | Denominator | Command |",
        "|---|---|---|---|---|",
    ]
    for claim in registry["claims"]:
        lines.append(
            f"| {claim['title']} | {claim['status']} | {claim['unit_of_analysis']} | "
            f"{claim['denominator']} | `{claim['reproduction_command']}` |"
        )
    lines.append("")
    lines.append("## Caveats")
    for claim in registry["claims"]:
        for caveat in claim["caveats"]:
            lines.append(f"- {claim['claim_id']}: {caveat}")
    lines.append("")
    return "\n".join(lines)
