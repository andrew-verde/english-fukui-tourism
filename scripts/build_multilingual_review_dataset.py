#!/usr/bin/env python3
"""
Build cached multilingual Google review analysis outputs.

This suite uses existing checkpoint JSON only. It does not call Google,
Outscraper, or any other collection API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from langdetect import DetectorFactory, detect
from scipy import stats

from src.friction.tagger import load_codebook, tag_dataframe
from src.official_fukui.ftas import load_japanese_codebook, tag_ftas_dataframe
from src.utils.logger import setup_logger

logger = setup_logger(__name__)
DetectorFactory.seed = 0

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoints"
DEFAULT_OUTPUT_DIR = OUTPUT_DIR / "multilingual_review_analysis"
METADATA_FILE = CHECKPOINT_DIR / "poi_metadata.json"
ENGLISH_CODEBOOK_PATH = ROOT / "config" / "friction_codebook.yaml"
JAPANESE_CODEBOOK_PATH = ROOT / "config" / "official_japanese_friction_codebook.yaml"

CITY_CHECKPOINT_MAP = {
    "Fukui": CHECKPOINT_DIR / "google_fukui.json",
    "Kanazawa": CHECKPOINT_DIR / "google_kanazawa.json",
    "Toyama": CHECKPOINT_DIR / "google_toyama.json",
}

DROP_UNPARSEABLE_TIMESTAMPS = os.getenv("DROP_UNPARSEABLE_TIMESTAMPS", "0").lower() in {"1", "true", "yes"}

SCHEMA_COLUMNS = [
    "city",
    "poi_id",
    "poi_name",
    "poi_category",
    "place_id",
    "review_id",
    "source_review_id",
    "review_date",
    "review_rating",
    "review_text",
    "provider_language",
    "detected_language",
    "language_group",
    "review_author",
    "collection_date",
    "source_platform",
    "review_order_within_poi",
]

LANGUAGE_GROUPS = ["english", "japanese", "other_non_english_non_japanese", "undetected_or_too_short"]

FRICTION_LABEL_JA = {
    "transport_access": "交通・アクセス",
    "wayfinding_signage": "案内・サイン",
    "english_information_gap": "英語・多言語情報不足",
    "staff_communication": "スタッフ対応・コミュニケーション",
    "booking_ticketing": "予約・チケット・決済",
    "waiting_crowding": "待ち時間・混雑",
    "price_value": "価格・価値",
    "cleanliness_comfort": "清潔さ・快適性",
    "opening_hours_availability": "営業時間・利用可否",
    "itinerary_fit_time_cost": "旅程適合・時間コスト",
    "accessibility_mobility": "アクセシビリティ・移動しやすさ",
    "food_amenities_gap": "飲食・設備不足",
}

NAME_CATEGORY_RULES = [
    (["museum", "gallery", "art museum", "washi", "pottery", "craft museum", "folk museum"], "museum_cultural"),
    (["temple", "shrine", "jingu", "daibutsu", "eiheiji", "hakusan"], "temple_shrine"),
    (["castle", "ruins", "asakura", "warehouse", "red brick", "yokokan"], "castle_historic"),
    (["onsen", "spa", "thermal", "awara", "unazuki"], "onsen_wellness"),
    (["market", "omicho", "kitokito", "himi fishing", "knife village"], "market_shopping"),
    (["cliff", "cave", "tojinbo", "gorge", "park", "garden", "river", "island", "port"], "nature_scenic"),
    (["food", "crab", "restaurant", "dining"], "food_dining"),
]


def _load_json(path: Path) -> dict:
    if not path.exists():
        logger.warning("Checkpoint not found: %s", path)
        return {}
    with open(path) as f:
        return json.load(f)


def _infer_category_from_name(poi_name: str) -> str:
    name_lower = poi_name.lower()
    for keywords, category in NAME_CATEGORY_RULES:
        if any(keyword in name_lower for keyword in keywords):
            return category
    return "other"


def _detect_language(text: object) -> str:
    if not isinstance(text, str):
        return "detect_error"
    text = text.strip()
    if len(text) < 4:
        return "too_short"
    try:
        return detect(text)
    except Exception:
        return "detect_error"


def _language_group(detected_language: str) -> str:
    if detected_language == "en":
        return "english"
    if detected_language == "ja":
        return "japanese"
    if detected_language in {"too_short", "detect_error"}:
        return "undetected_or_too_short"
    return "other_non_english_non_japanese"


def _stable_review_id(city: str, place_id: str, poi_name: str, order: int, review: dict) -> str:
    source_key = review.get("source_review_id") or review.get("review_url")
    if source_key:
        raw = f"{city}_{place_id or poi_name}_{source_key}"
    else:
        raw = f"{city}_{place_id or poi_name}_{poi_name}_{order}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _passes_cutoff(timestamp: str, cutoff: str, stats: Counter) -> bool:
    if not cutoff:
        return True
    if not timestamp:
        stats["missing_timestamp"] += 1
        return True
    try:
        parsed = pd.to_datetime(timestamp, format="mixed", utc=True)
        cutoff_ts = pd.Timestamp(cutoff, tz="UTC")
    except Exception:
        stats["unparseable_timestamp"] += 1
        if DROP_UNPARSEABLE_TIMESTAMPS:
            stats["dropped_unparseable_timestamp"] += 1
            return False
        return True
    if parsed < cutoff_ts:
        stats["dropped_by_cutoff"] += 1
        return False
    return True


def _metadata_category(metadata: dict, place_id: str, poi_name: str) -> str:
    meta = metadata.get(place_id, {}) if place_id else {}
    category = meta.get("poi_category", "other")
    if category == "other" or not meta.get("types"):
        category = _infer_category_from_name(poi_name)
    return category


def parse_checkpoint_rows(city: str, data: dict, metadata: dict, cutoff: str, stats: Counter) -> list[dict]:
    rows = []
    collection_date = str(date.today())
    for poi_name, poi_data in data.items():
        if isinstance(poi_data, dict):
            reviews = poi_data.get("reviews", [])
            checkpoint_source = poi_data.get("source_platform") or "google_places"
        elif isinstance(poi_data, list):
            reviews = poi_data
            checkpoint_source = "google_places"
        else:
            continue

        for order, review in enumerate(reviews):
            text = review.get("review_text", "") or ""
            if not text.strip():
                stats["missing_text"] += 1
                continue

            timestamp = review.get("timestamp", "") or ""
            if not _passes_cutoff(timestamp, cutoff, stats):
                continue

            place_id = review.get("place_id", "") or ""
            detected_language = _detect_language(text)
            rows.append({
                "city": city,
                "poi_id": place_id or poi_name,
                "poi_name": poi_name,
                "poi_category": _metadata_category(metadata, place_id, poi_name),
                "place_id": place_id,
                "review_id": _stable_review_id(city, place_id, poi_name, order, review),
                "source_review_id": review.get("source_review_id", ""),
                "review_date": timestamp,
                "review_rating": review.get("rating"),
                "review_text": text,
                "provider_language": review.get("language", ""),
                "detected_language": detected_language,
                "language_group": _language_group(detected_language),
                "review_author": review.get("author_name", ""),
                "collection_date": collection_date,
                "source_platform": review.get("source_platform") or checkpoint_source,
                "review_order_within_poi": order,
            })
    return rows


def _counts_table(df: pd.DataFrame, index_col: str, col_col: str) -> pd.DataFrame:
    table = pd.crosstab(df[index_col], df[col_col])
    return table.reset_index()


def _rating_summary(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    ratings = df.copy()
    ratings["review_rating"] = pd.to_numeric(ratings["review_rating"], errors="coerce")
    grouped = ratings.groupby(group_cols, dropna=False)["review_rating"]
    return grouped.agg(["count", "mean", "median", "std"]).reset_index()


def _tag_language_friction(df: pd.DataFrame, english_codebook: dict, japanese_codebook: dict) -> pd.DataFrame:
    tagged_parts = []
    english = df[df["language_group"] == "english"].copy()
    if not english.empty:
        tagged_parts.append(tag_dataframe(english, "review_text", english_codebook))

    japanese = df[df["language_group"] == "japanese"].copy()
    if not japanese.empty:
        tagged_parts.append(tag_ftas_dataframe(japanese, "review_text", japanese_codebook))

    other = df[~df["language_group"].isin({"english", "japanese"})].copy()
    all_codes = sorted(set(english_codebook.keys()) | set(japanese_codebook.keys()))
    if not other.empty:
        for code in all_codes:
            other[code] = False
        other["friction_codes"] = [[] for _ in range(len(other))]
        other["any_friction"] = False
        tagged_parts.append(other)

    tagged = pd.concat(tagged_parts, ignore_index=True, sort=False) if tagged_parts else df.copy()
    for code in all_codes:
        if code not in tagged.columns:
            tagged[code] = False
        tagged[code] = tagged[code].fillna(False).astype(bool)
    friction_codes = sorted(
        {
            code
            for code, attrs in {**english_codebook, **japanese_codebook}.items()
            if attrs.get("type") == "friction"
        }
    )
    tagged["any_friction"] = tagged[friction_codes].any(axis=1) if friction_codes else False
    return tagged


def _friction_summary(tagged: pd.DataFrame, codebook: dict) -> pd.DataFrame:
    codes = [code for code, attrs in codebook.items() if attrs.get("type") == "friction"]
    rows = []
    grouped = tagged[tagged["language_group"].isin({"english", "japanese"})].groupby(["city", "language_group"], dropna=False)
    for (city, language_group), group in grouped:
        denominator = len(group)
        for code in codes:
            count = int(group[code].sum()) if code in group.columns else 0
            rows.append({
                "city": city,
                "language_group": language_group,
                "code": code,
                "label": codebook[code]["label"],
                "count": count,
                "denominator_reviews": denominator,
                "pct_reviews": round(100 * count / denominator, 3) if denominator else 0.0,
            })
    return pd.DataFrame(rows)


def _bh_adjust(p_values: list[float | None]) -> list[float | None]:
    indexed = [
        (idx, float(p))
        for idx, p in enumerate(p_values)
        if p is not None and pd.notna(p)
    ]
    if not indexed:
        return [None for _ in p_values]
    m = len(indexed)
    adjusted = [None for _ in p_values]
    ranked = sorted(indexed, key=lambda item: item[1])
    raw_adjusted = [
        (idx, min(p * m / rank, 1.0))
        for rank, (idx, p) in enumerate(ranked, start=1)
    ]
    running = 1.0
    for idx, value in reversed(raw_adjusted):
        running = min(running, value)
        adjusted[idx] = running
    return adjusted


def _cramers_v_2x2(table: list[list[int]], chi2: float) -> float | None:
    n = sum(sum(row) for row in table)
    if n <= 0:
        return None
    return float((chi2 / n) ** 0.5)


def _english_japanese_comparison(tagged: pd.DataFrame, codebook: dict) -> pd.DataFrame:
    """Compare English and Japanese review-level friction rates by city/code."""
    codes = [code for code, attrs in codebook.items() if attrs.get("type") == "friction"]
    rows = []
    comparable = tagged[tagged["language_group"].isin({"english", "japanese"})].copy()
    for city, city_df in comparable.groupby("city", dropna=False):
        english = city_df[city_df["language_group"] == "english"]
        japanese = city_df[city_df["language_group"] == "japanese"]
        english_n = len(english)
        japanese_n = len(japanese)
        for code in codes:
            english_count = int(english[code].sum()) if code in english.columns else 0
            japanese_count = int(japanese[code].sum()) if code in japanese.columns else 0
            english_no = english_n - english_count
            japanese_no = japanese_n - japanese_count
            table = [[english_count, english_no], [japanese_count, japanese_no]]
            fisher_p = None
            odds_ratio = None
            chi2_p = None
            cramers_v = None
            if english_n and japanese_n:
                try:
                    odds_ratio, fisher_p = stats.fisher_exact(table, alternative="two-sided")
                    odds_ratio = float(odds_ratio)
                    fisher_p = float(fisher_p)
                except Exception:
                    odds_ratio = None
                    fisher_p = None
                try:
                    chi2, chi2_p, _dof, _expected = stats.chi2_contingency(table)
                    chi2_p = float(chi2_p)
                    cramers_v = _cramers_v_2x2(table, float(chi2))
                except Exception:
                    chi2_p = None
                    cramers_v = None
            english_pct = 100 * english_count / english_n if english_n else 0.0
            japanese_pct = 100 * japanese_count / japanese_n if japanese_n else 0.0
            rows.append({
                "city": city,
                "friction_code": code,
                "friction_label": codebook[code]["label"],
                "friction_label_ja": FRICTION_LABEL_JA.get(code, ""),
                "friction_label_with_ja": f"{codebook[code]['label']} ({FRICTION_LABEL_JA.get(code, code)})",
                "english_count": english_count,
                "english_n": english_n,
                "english_pct_reviews": round(english_pct, 3),
                "japanese_count": japanese_count,
                "japanese_n": japanese_n,
                "japanese_pct_reviews": round(japanese_pct, 3),
                "japanese_minus_english_pp": round(japanese_pct - english_pct, 3),
                "odds_ratio_english_vs_japanese": odds_ratio,
                "fisher_exact_p": fisher_p,
                "chi_square_p": chi2_p,
                "cramers_v": cramers_v,
            })
    comparison = pd.DataFrame(rows)
    if not comparison.empty:
        comparison["fisher_exact_p_bh"] = _bh_adjust(comparison["fisher_exact_p"].tolist())
        comparison["significant_bh_0_05"] = comparison["fisher_exact_p_bh"].apply(
            lambda value: bool(pd.notna(value) and value < 0.05)
        )
    return comparison


def _write_japanese_friction_report(
    friction_summary: pd.DataFrame,
    comparison: pd.DataFrame,
    path: Path,
) -> None:
    lines = [
        "# Japanese Review Friction Analysis",
        "",
        "This report uses cached Google review checkpoints only. It compares detected Japanese-language reviews with detected English-language reviews; language is not reviewer nationality.",
        "",
        "Friction labels are shown as English label (Japanese translation). Rates use review-level denominators so English and Japanese review samples can be compared directly.",
        "",
        "## Top Japanese Friction Points by City",
        "",
    ]
    japanese = friction_summary[friction_summary["language_group"] == "japanese"].copy()
    for city in sorted(japanese["city"].dropna().unique()):
        lines.extend([f"### {city}", ""])
        top = japanese[japanese["city"] == city].sort_values(["count", "pct_reviews"], ascending=False).head(6)
        if top.empty:
            lines.append("- No Japanese friction codes detected.")
        else:
            for _, row in top.iterrows():
                label_ja = FRICTION_LABEL_JA.get(row["code"], row["code"])
                lines.append(
                    f"- {row['label']} ({label_ja}): {int(row['count'])} / "
                    f"{int(row['denominator_reviews'])} reviews ({float(row['pct_reviews']):.2f}%)."
                )
        lines.append("")

    lines.extend([
        "## English vs Japanese Review Comparison",
        "",
        "Fisher exact p-values are used as the main comparison because some English review cells are sparse. BH correction is applied across all city-code comparisons.",
        "",
    ])
    if comparison.empty:
        lines.append("- No comparable English/Japanese review rows found.")
    else:
        highlights = comparison.sort_values("fisher_exact_p_bh", na_position="last").head(10)
        for _, row in highlights.iterrows():
            direction = "higher in Japanese" if row["japanese_minus_english_pp"] > 0 else "higher in English"
            p_bh = row.get("fisher_exact_p_bh")
            p_text = f"{float(p_bh):.3g}" if pd.notna(p_bh) else "NA"
            lines.append(
                f"- {row['city']} — {row['friction_label_with_ja']}: "
                f"English {int(row['english_count'])}/{int(row['english_n'])} "
                f"({float(row['english_pct_reviews']):.2f}%), Japanese "
                f"{int(row['japanese_count'])}/{int(row['japanese_n'])} "
                f"({float(row['japanese_pct_reviews']):.2f}%), "
                f"{direction} by {abs(float(row['japanese_minus_english_pp'])):.2f} pp; "
                f"Fisher p_BH={p_text}."
            )
    lines.extend([
        "",
        "## Caveats",
        "",
        "- The Japanese and English codebooks are mirrored by code label, but they are keyword rules rather than a validated cross-language classifier.",
        "- Japanese substring matching can overcount broad terms such as stairs, signs, or English unless manually validated.",
        "- English review counts are much smaller than Japanese review counts, so sparse-cell p-values and effect sizes should be interpreted descriptively.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Multilingual Cached Review Analysis",
        "",
        "This analysis uses cached checkpoint files only. It does not call Google, Outscraper, or any paid collection API.",
        "",
        f"- Review date cutoff: `{report['review_date_cutoff'] or 'none'}`",
        f"- Rows before deduplication: {report['rows_before_dedup']}",
        f"- Duplicate city/text rows removed: {report['duplicates_removed']}",
        f"- Rows retained: {report['rows_retained']}",
        f"- Dropped by cutoff: {report['dropped_by_cutoff']}",
        f"- Missing timestamps retained: {report['missing_timestamp']}",
        f"- Unparseable timestamps retained: {report['unparseable_timestamp']}",
        "",
        "## Language Groups",
        "",
        "| Language group | Reviews |",
        "|---|---:|",
    ]
    for group in LANGUAGE_GROUPS:
        lines.append(f"| {group} | {report['language_group_counts'].get(group, 0)} |")
    lines.extend([
        "",
        "## Caveats",
        "",
        "- Review language is not reviewer nationality or residency.",
        "- Japanese review friction uses the Japanese keyword codebook; English review friction uses the English codebook. Labels are mirrored, but keyword coverage is not a validated cross-language classifier.",
        "- Other non-English/non-Japanese reviews are summarized by language and ratings only unless separate codebooks or translation are added.",
        "- Very short reviews can be marked `undetected_or_too_short`; they are kept in the multilingual dataset but excluded from the other-language proxy segment.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def build_multilingual_outputs(
    cutoff: str,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    checkpoint_map: dict[str, Path] | None = None,
    metadata_file: Path = METADATA_FILE,
) -> dict:
    checkpoint_map = checkpoint_map or CITY_CHECKPOINT_MAP
    missing = [str(path) for path in checkpoint_map.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing Google review checkpoint input(s): "
            + ", ".join(missing)
            + ". Recreate them with make fetch-fukui-data, make fetch-comparison-data, "
            "or make fetch-google-maps-reviews before rebuilding multilingual outputs."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = _load_json(metadata_file)
    stats: Counter = Counter()
    rows = []
    for city, path in checkpoint_map.items():
        logger.info("Processing %s from %s", city, path)
        rows.extend(parse_checkpoint_rows(city, _load_json(path), metadata, cutoff, stats))

    df = pd.DataFrame(rows, columns=SCHEMA_COLUMNS)
    rows_before_dedup = len(df)
    if not df.empty:
        df = df.drop_duplicates(subset=["city", "review_text"], keep="first").reset_index(drop=True)
    duplicates_removed = rows_before_dedup - len(df)

    english_codebook = load_codebook(ENGLISH_CODEBOOK_PATH)
    japanese_codebook = load_japanese_codebook(JAPANESE_CODEBOOK_PATH)
    tagged = _tag_language_friction(df, english_codebook, japanese_codebook) if not df.empty else df.copy()

    reviews_path = output_dir / "reviews_multilingual.csv"
    tagged_path = output_dir / "tagged_reviews_multilingual.csv"
    language_city_path = output_dir / "language_summary_by_city.csv"
    rating_path = output_dir / "rating_summary_by_city_language_group.csv"
    japanese_path = output_dir / "japanese_reviews_tagged.csv"
    japanese_friction_path = output_dir / "japanese_friction_by_city.csv"
    japanese_english_comparison_path = output_dir / "japanese_english_friction_comparison.csv"
    japanese_report_path = output_dir / "japanese_review_friction_analysis.md"
    other_path = output_dir / "non_english_non_japanese_reviews.csv"
    other_language_path = output_dir / "other_foreign_language_summary_by_city.csv"
    friction_path = output_dir / "friction_by_city_language_group.csv"
    report_json_path = output_dir / "multilingual_readiness.json"
    report_md_path = output_dir / "multilingual_readiness.md"

    df.to_csv(reviews_path, index=False)
    tagged.to_csv(tagged_path, index=False)
    _counts_table(df, "city", "language_group").to_csv(language_city_path, index=False)
    _rating_summary(df, ["city", "language_group"]).to_csv(rating_path, index=False)

    japanese = tagged[tagged["language_group"] == "japanese"].copy()
    japanese.to_csv(japanese_path, index=False)
    japanese_friction = _friction_summary(japanese, japanese_codebook)
    japanese_friction.to_csv(japanese_friction_path, index=False)

    other = df[df["language_group"] == "other_non_english_non_japanese"].copy()
    other.to_csv(other_path, index=False)
    _counts_table(other, "city", "detected_language").to_csv(other_language_path, index=False)
    friction_summary = _friction_summary(tagged, japanese_codebook)
    friction_summary.to_csv(friction_path, index=False)
    japanese_english_comparison = _english_japanese_comparison(tagged, japanese_codebook)
    japanese_english_comparison.to_csv(japanese_english_comparison_path, index=False)
    _write_japanese_friction_report(friction_summary, japanese_english_comparison, japanese_report_path)

    report = {
        "review_date_cutoff": cutoff,
        "rows_before_dedup": rows_before_dedup,
        "duplicates_removed": duplicates_removed,
        "rows_retained": len(df),
        "dropped_by_cutoff": int(stats["dropped_by_cutoff"]),
        "missing_timestamp": int(stats["missing_timestamp"]),
        "unparseable_timestamp": int(stats["unparseable_timestamp"]),
        "dropped_unparseable_timestamp": int(stats["dropped_unparseable_timestamp"]),
        "missing_text": int(stats["missing_text"]),
        "language_group_counts": {group: int((df["language_group"] == group).sum()) for group in LANGUAGE_GROUPS} if not df.empty else {},
        "detected_language_counts": {str(k): int(v) for k, v in df["detected_language"].value_counts().to_dict().items()} if not df.empty else {},
        "outputs": {
            "reviews_multilingual": str(reviews_path),
            "tagged_reviews_multilingual": str(tagged_path),
            "language_summary_by_city": str(language_city_path),
            "rating_summary_by_city_language_group": str(rating_path),
            "japanese_reviews_tagged": str(japanese_path),
            "japanese_friction_by_city": str(japanese_friction_path),
            "japanese_english_friction_comparison": str(japanese_english_comparison_path),
            "japanese_review_friction_analysis": str(japanese_report_path),
            "non_english_non_japanese_reviews": str(other_path),
            "other_foreign_language_summary_by_city": str(other_language_path),
            "friction_by_city_language_group": str(friction_path),
        },
    }
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, report_md_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cutoff",
        default=os.getenv("REVIEW_DATE_CUTOFF", "2024-06-01"),
        help="Drop reviews before this date. Defaults to REVIEW_DATE_CUTOFF or 2024-06-01.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger.info("=" * 55)
    logger.info("Build multilingual cached review analysis")
    logger.info("  Date cutoff: %s", args.cutoff or "none")
    logger.info("  Output dir: %s", args.output_dir)
    logger.info("=" * 55)
    report = build_multilingual_outputs(cutoff=args.cutoff, output_dir=args.output_dir)
    logger.info("Rows retained: %s", report["rows_retained"])
    for group, count in report["language_group_counts"].items():
        logger.info("  %-34s %s", group, count)
    logger.info("Output written: %s", args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
