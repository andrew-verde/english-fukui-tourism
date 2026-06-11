#!/usr/bin/env python3
"""
Build Chinese social-media tourism text analysis outputs.

The input layer is schema-first and empty-data-safe. It normalizes Xiaohongshu
and Douyin CSV exports from the companion tourism-data project into a
review-like row schema, then applies Chinese friction keywords and transparent
lexicon sentiment fields for comparison with the Google-review layers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from itertools import combinations
from pathlib import Path

import pandas as pd
import yaml
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = Path("/Users/andrewgreen/Repositories/tourism-data")
OUTPUT_DIR = ROOT / "output" / "chinese_social_media_analysis"
CODEBOOK_PATH = ROOT / "config" / "chinese_social_friction_codebook.yaml"
MULTILINGUAL_FRICTION_PATH = ROOT / "output" / "multilingual_review_analysis" / "friction_by_city_language_group.csv"

SOURCE_COLUMNS = [
    "city",
    "source_platform",
    "source_file",
    "source_record_id",
    "source_url",
    "author",
    "author_url",
    "title",
    "text_content",
]

SCHEMA_COLUMNS = [
    *SOURCE_COLUMNS,
    "content_language",
    "record_id",
    "sentiment_score",
    "sentiment_norm",
    "emotional_intensity_score",
]

POSITIVE_TERMS = [
    "好", "方便", "便利", "推荐", "值得", "喜欢", "美", "震撼", "舒服", "干净",
    "热情", "新鲜", "便宜", "顺利", "梦幻", "完善", "直达",
]

NEGATIVE_TERMS = [
    "不便", "不方便", "差", "贵", "拥挤", "排队", "少", "旧", "脏", "难",
    "堵", "累", "坑", "售罄", "关门", "没开", "找不到", "看不懂",
]

CITY_ALIASES = {
    "fukui": "Fukui",
    "福井": "Fukui",
    "kanazawa": "Kanazawa",
    "金泽": "Kanazawa",
    "金沢": "Kanazawa",
    "toyama": "Toyama",
    "富山": "Toyama",
}

PLATFORM_ALIASES = {
    "xhs": "xiaohongshu",
    "xiaohongshu": "xiaohongshu",
    "小红书": "xiaohongshu",
    "douyin": "douyin",
    "抖音": "douyin",
}


def load_chinese_codebook(path: Path = CODEBOOK_PATH) -> dict:
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    codebook = {}
    for code, attrs in raw.get("friction_codes", {}).items():
        codebook[code] = {
            "label": attrs["label"],
            "type": attrs["type"],
            "keywords": [str(keyword) for keyword in attrs.get("keywords", [])],
        }
    return codebook


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return re.sub(r"\s+", " ", text)


def _infer_city(path: Path, row: pd.Series) -> str:
    explicit = _clean_text(row.get("city", ""))
    haystack = " ".join([explicit, path.stem, path.name]).lower()
    for token, city in CITY_ALIASES.items():
        if token.lower() in haystack:
            return city
    return explicit or "Unknown"


def _infer_platform(path: Path, row: pd.Series) -> str:
    explicit = _clean_text(row.get("source_platform", "")) or _clean_text(row.get("platform", ""))
    haystack = " ".join([explicit, path.stem, path.name]).lower()
    for token, platform in PLATFORM_ALIASES.items():
        if token.lower() in haystack:
            return platform
    return explicit or "unknown"


def _source_record_id(row: pd.Series, platform: str) -> str:
    candidates = ["source_record_id", "note_id", "video_id", "id", "note_url", "video_url", "url"]
    for field in candidates:
        value = _clean_text(row.get(field, ""))
        if value:
            return value
    raw = "|".join(_clean_text(row.get(field, "")) for field in row.index)
    return hashlib.sha256(f"{platform}|{raw}".encode()).hexdigest()[:12]


def _source_url(row: pd.Series) -> str:
    for field in ["source_url", "note_url", "video_url", "url"]:
        value = _clean_text(row.get(field, ""))
        if value:
            return value
    return ""


def _record_id(city: str, platform: str, source_record_id: str, text: str) -> str:
    raw = f"{city}|{platform}|{source_record_id}|{text}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _lexicon_sentiment(text: str) -> tuple[float, float, float]:
    if not text:
        return 0.0, 0.5, 0.0
    positive = sum(text.count(term) for term in POSITIVE_TERMS)
    negative = sum(text.count(term) for term in NEGATIVE_TERMS)
    total = positive + negative
    score = (positive - negative) / total if total else 0.0
    return round(score, 6), round((score + 1.0) / 2.0, 6), round(abs(score), 6)


def _read_input_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def discover_input_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    files = []
    for path in input_dir.glob("*.csv"):
        name = path.name.lower()
        if any(token in name for token in ["xhs", "xiaohongshu", "douyin", "小红书", "抖音"]):
            files.append(path)
    return sorted(files)


def normalize_social_csv(path: Path) -> pd.DataFrame:
    source = _read_input_csv(path)
    if source.empty:
        return pd.DataFrame(columns=SCHEMA_COLUMNS)

    rows = []
    for _, row in source.iterrows():
        title = _clean_text(row.get("title", ""))
        body = _clean_text(row.get("text", "")) or _clean_text(row.get("description", "")) or _clean_text(row.get("content", ""))
        text_content = " ".join(part for part in [title, body] if part).strip()
        if not text_content:
            continue

        city = _infer_city(path, row)
        platform = _infer_platform(path, row)
        source_record_id = _source_record_id(row, platform)
        sentiment_score, sentiment_norm, intensity = _lexicon_sentiment(text_content)
        rows.append({
            "city": city,
            "source_platform": platform,
            "source_file": str(path),
            "source_record_id": source_record_id,
            "source_url": _source_url(row),
            "author": _clean_text(row.get("author", "")),
            "author_url": _clean_text(row.get("author_url", "")),
            "title": title,
            "text_content": text_content,
            "content_language": "zh",
            "record_id": _record_id(city, platform, source_record_id, text_content),
            "sentiment_score": sentiment_score,
            "sentiment_norm": sentiment_norm,
            "emotional_intensity_score": intensity,
        })
    return pd.DataFrame(rows, columns=SCHEMA_COLUMNS)


def _tag_chinese_dataframe(df: pd.DataFrame, codebook: dict) -> pd.DataFrame:
    tagged = df.copy()
    for code, attrs in codebook.items():
        keywords = attrs["keywords"]
        tagged[code] = tagged["text_content"].apply(
            lambda text, keywords=keywords: any(keyword in str(text) for keyword in keywords)
        )
    friction_codes = [code for code, attrs in codebook.items() if attrs["type"] == "friction"]
    if friction_codes:
        tagged["friction_codes"] = tagged[friction_codes].apply(
            lambda row: [code for code in friction_codes if bool(row[code])],
            axis=1,
        )
        tagged["any_friction"] = tagged[friction_codes].any(axis=1)
    else:
        tagged["friction_codes"] = [[] for _ in range(len(tagged))]
        tagged["any_friction"] = False
    return tagged


def _friction_summary(tagged: pd.DataFrame, codebook: dict) -> pd.DataFrame:
    rows = []
    codes = [code for code, attrs in codebook.items() if attrs["type"] == "friction"]
    grouped = tagged.groupby(["city", "source_platform"], dropna=False)
    for (city, platform), group in grouped:
        denominator = len(group)
        for code in codes:
            count = int(group[code].sum()) if code in group.columns else 0
            rows.append({
                "city": city,
                "source_platform": platform,
                "friction_code": code,
                "friction_label": codebook[code]["label"],
                "count": count,
                "denominator_posts": denominator,
                "pct_posts": round(100 * count / denominator, 3) if denominator else 0.0,
            })
    return pd.DataFrame(rows)


def _sentiment_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["city", "source_platform", "count", "mean", "median", "std"])
    grouped = df.groupby(["city", "source_platform"], dropna=False)["sentiment_norm"]
    return grouped.agg(["count", "mean", "median", "std"]).reset_index()


def _binary_group_test(df: pd.DataFrame, group_col: str, code: str) -> list[dict]:
    rows = []
    groups = sorted(str(value) for value in df[group_col].dropna().unique())
    for a, b in combinations(groups, 2):
        ga = df[df[group_col].astype(str) == a]
        gb = df[df[group_col].astype(str) == b]
        a_count = int(ga[code].sum())
        b_count = int(gb[code].sum())
        table = [[a_count, len(ga) - a_count], [b_count, len(gb) - b_count]]
        fisher_p = None
        odds_ratio = None
        if len(ga) and len(gb):
            try:
                odds_ratio, fisher_p = stats.fisher_exact(table, alternative="two-sided")
            except Exception:
                pass
        rows.append({
            "comparison_type": group_col,
            "group_a": a,
            "group_b": b,
            "friction_code": code,
            "group_a_count": a_count,
            "group_a_n": int(len(ga)),
            "group_b_count": b_count,
            "group_b_n": int(len(gb)),
            "group_a_pct": round(100 * a_count / len(ga), 3) if len(ga) else 0.0,
            "group_b_pct": round(100 * b_count / len(gb), 3) if len(gb) else 0.0,
            "group_b_minus_group_a_pp": round(
                (100 * b_count / len(gb) if len(gb) else 0.0)
                - (100 * a_count / len(ga) if len(ga) else 0.0),
                3,
            ),
            "odds_ratio": None if odds_ratio is None else float(odds_ratio),
            "fisher_exact_p": None if fisher_p is None else float(fisher_p),
        })
    return rows


def _within_chinese_tests(tagged: pd.DataFrame, codebook: dict) -> pd.DataFrame:
    rows = []
    codes = [code for code, attrs in codebook.items() if attrs["type"] == "friction"]
    for code in codes:
        rows.extend(_binary_group_test(tagged, "city", code))
        rows.extend(_binary_group_test(tagged, "source_platform", code))
    return pd.DataFrame(rows)


def _review_language_comparison(friction_summary: pd.DataFrame, review_path: Path) -> pd.DataFrame:
    columns = [
        "city", "friction_code", "friction_label", "comparison_group",
        "chinese_count", "chinese_n", "chinese_pct_posts",
        "review_count", "review_n", "review_pct_reviews",
        "review_minus_chinese_pp",
    ]
    if friction_summary.empty or not review_path.exists():
        return pd.DataFrame(columns=columns)
    reviews = pd.read_csv(review_path)
    if reviews.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    chinese = friction_summary.groupby(["city", "friction_code", "friction_label"], dropna=False).agg(
        chinese_count=("count", "sum"),
        chinese_n=("denominator_posts", "sum"),
    ).reset_index()
    chinese["chinese_pct_posts"] = chinese.apply(
        lambda row: round(100 * row["chinese_count"] / row["chinese_n"], 3) if row["chinese_n"] else 0.0,
        axis=1,
    )
    for _, row in chinese.iterrows():
        comparable = reviews[
            (reviews["city"] == row["city"])
            & (reviews["code"] == row["friction_code"])
            & (reviews["language_group"].isin(["english", "japanese"]))
        ]
        for _, review_row in comparable.iterrows():
            rows.append({
                "city": row["city"],
                "friction_code": row["friction_code"],
                "friction_label": row["friction_label"],
                "comparison_group": f"google_{review_row['language_group']}",
                "chinese_count": int(row["chinese_count"]),
                "chinese_n": int(row["chinese_n"]),
                "chinese_pct_posts": float(row["chinese_pct_posts"]),
                "review_count": int(review_row["count"]),
                "review_n": int(review_row["denominator_reviews"]),
                "review_pct_reviews": float(review_row["pct_reviews"]),
                "review_minus_chinese_pp": round(float(review_row["pct_reviews"]) - float(row["chinese_pct_posts"]), 3),
            })
    return pd.DataFrame(rows, columns=columns)


def _write_readiness(report: dict, path: Path) -> None:
    lines = [
        "# Chinese Social Media Analysis Readiness",
        "",
        "This layer treats Xiaohongshu notes and Douyin videos as Chinese-language recommendation text, analogous to the role Google reviews play for English-language review analysis. It is not a nationality inference.",
        "",
        f"- Input directory: `{report['input_dir']}`",
        f"- Input files discovered: {report['input_files_discovered']}",
        f"- Rows before deduplication: {report['rows_before_dedup']}",
        f"- Duplicate city/platform/text rows removed: {report['duplicates_removed']}",
        f"- Rows retained: {report['rows_retained']}",
        "",
        "## Caveats",
        "",
        "- Unit of analysis is one social-media search result row, currently title/text-level, not a full travel itinerary or confirmed visit.",
        "- Chinese friction tags are substring keyword matches and need manual validation once populated rows exist.",
        "- Sentiment fields use a transparent keyword polarity scaffold, not VADER and not a validated Chinese sentiment model.",
        "- Compare Chinese social-media rates with Google review-language rates descriptively because source platform behavior and text length differ.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def build_chinese_social_outputs(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = OUTPUT_DIR,
    input_files: list[Path] | None = None,
    review_friction_path: Path = MULTILINGUAL_FRICTION_PATH,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    input_files = input_files if input_files is not None else discover_input_files(input_dir)
    codebook = load_chinese_codebook()

    frames = [normalize_social_csv(path) for path in input_files]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=SCHEMA_COLUMNS)
    rows_before_dedup = len(df)
    if not df.empty:
        df = df.drop_duplicates(subset=["city", "source_platform", "text_content"], keep="first").reset_index(drop=True)
    duplicates_removed = rows_before_dedup - len(df)

    tagged = _tag_chinese_dataframe(df, codebook) if not df.empty else df.copy()
    for code in codebook:
        if code not in tagged.columns:
            tagged[code] = pd.Series(dtype=bool)
    if "friction_codes" not in tagged.columns:
        tagged["friction_codes"] = pd.Series(dtype=object)
    if "any_friction" not in tagged.columns:
        tagged["any_friction"] = pd.Series(dtype=bool)

    normalized_path = output_dir / "chinese_social_posts.csv"
    tagged_path = output_dir / "tagged_chinese_social_posts.csv"
    friction_summary_path = output_dir / "chinese_friction_by_city_platform.csv"
    sentiment_summary_path = output_dir / "chinese_sentiment_by_city_platform.csv"
    within_tests_path = output_dir / "chinese_city_platform_friction_tests.csv"
    review_comparison_path = output_dir / "chinese_vs_review_language_friction_comparison.csv"
    report_json_path = output_dir / "chinese_social_readiness.json"
    report_md_path = output_dir / "chinese_social_readiness.md"

    friction_summary = _friction_summary(tagged, codebook) if not tagged.empty else pd.DataFrame(
        columns=["city", "source_platform", "friction_code", "friction_label", "count", "denominator_posts", "pct_posts"]
    )
    sentiment_summary = _sentiment_summary(df)
    within_tests = _within_chinese_tests(tagged, codebook) if not tagged.empty else pd.DataFrame()
    review_comparison = _review_language_comparison(friction_summary, review_friction_path)

    df.to_csv(normalized_path, index=False)
    tagged.to_csv(tagged_path, index=False)
    friction_summary.to_csv(friction_summary_path, index=False)
    sentiment_summary.to_csv(sentiment_summary_path, index=False)
    within_tests.to_csv(within_tests_path, index=False)
    review_comparison.to_csv(review_comparison_path, index=False)

    report = {
        "input_dir": str(input_dir),
        "input_files": [str(path) for path in input_files],
        "input_files_discovered": len(input_files),
        "rows_before_dedup": rows_before_dedup,
        "duplicates_removed": duplicates_removed,
        "rows_retained": len(df),
        "source_platform_counts": {str(k): int(v) for k, v in df["source_platform"].value_counts().items()} if not df.empty else {},
        "city_counts": {str(k): int(v) for k, v in df["city"].value_counts().items()} if not df.empty else {},
        "outputs": {
            "chinese_social_posts": str(normalized_path),
            "tagged_chinese_social_posts": str(tagged_path),
            "chinese_friction_by_city_platform": str(friction_summary_path),
            "chinese_sentiment_by_city_platform": str(sentiment_summary_path),
            "chinese_city_platform_friction_tests": str(within_tests_path),
            "chinese_vs_review_language_friction_comparison": str(review_comparison_path),
            "chinese_social_readiness": str(report_md_path),
        },
    }
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_readiness(report, report_md_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--input-file", type=Path, action="append", default=None, help="Specific CSV file to include; can be repeated.")
    parser.add_argument("--review-friction-path", type=Path, default=MULTILINGUAL_FRICTION_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_chinese_social_outputs(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        input_files=args.input_file,
        review_friction_path=args.review_friction_path,
    )
    logger.info("Rows retained: %s", report["rows_retained"])
    logger.info("Output written: %s", args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
