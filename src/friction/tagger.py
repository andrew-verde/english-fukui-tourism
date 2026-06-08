"""
tagger.py — Apply friction/nudge codebook to review or mention text.

Codebook is loaded from config/friction_codebook.yaml.
Keyword matching uses word-boundary regex (case-insensitive).
Multi-word phrases are matched as-is (spaces preserved).

Negation handling: if a negation word (not, less, never, wasn't, etc.)
appears within 4 words before a keyword match, the match is suppressed.
This prevents "not crowded", "less crowded", "wasn't busy" from being
tagged as friction.
"""

import re
from pathlib import Path

import pandas as pd
import yaml

# Words that, when appearing within 4 words before a matched keyword,
# indicate the keyword is negated and should NOT count as a friction signal.
_NEGATIONS = {
    "not", "no", "never", "less", "fewer", "neither", "nor",
    "wasn't", "weren't", "isn't", "aren't", "won't", "wouldn't",
    "doesn't", "don't", "didn't", "couldn't", "can't", "cannot",
    "without", "hardly", "barely", "rarely", "seldom",
}

# Compile once: captures up to 4 words before a position
_LOOKBEHIND_N = 4


def load_codebook(path: str | Path | None = None) -> dict:
    """
    Load the friction codebook from YAML.
    Defaults to config/friction_codebook.yaml relative to repo root.
    Returns a flat dict: code_name -> {label, type, keywords}.
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent.parent / "config" / "friction_codebook.yaml"

    with open(path) as f:
        raw = yaml.safe_load(f)

    codebook = {}
    for section in ("friction_codes", "nudge_codes"):
        for code, attrs in raw.get(section, {}).items():
            codebook[code] = {
                "label": attrs["label"],
                "type": attrs["type"],
                "keywords": [str(kw).lower() for kw in attrs.get("keywords", [])],
            }
    return codebook


def _normalize_quotes(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'").replace("`", "'")


def _make_pattern(keyword: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)


def _is_negated(text: str, match: re.Match) -> bool:
    """
    Return True if a negation word appears within _LOOKBEHIND_N words
    immediately before the match start position.
    """
    before = text[:match.start()]
    words_before = re.findall(r"\b[\w']+\b", before)[-_LOOKBEHIND_N:]
    return any(w.lower() in _NEGATIONS for w in words_before)


def _keyword_matches(text: str, keyword: str) -> bool:
    """
    Return True if keyword matches in text and is NOT preceded by a negation.

    Compound keywords:
      - If keyword contains '&&', all sub-keywords must match somewhere in text.
        This allows higher-recall patterns while keeping some precision
        (e.g. 'stairs && steep', 'busy && too').

    Keywords that begin with a negation word (e.g. 'no food', 'not worth',
    'nowhere to eat') encode negation explicitly — skip the lookbehind.
    All other keywords (single- or multi-word) are subject to negation checking,
    so 'not too crowded' does not match 'too crowded'.
    """
    text = _normalize_quotes(text)
    keyword = _normalize_quotes(keyword)

    if "&&" in keyword:
        parts = [p.strip() for p in keyword.split("&&") if p.strip()]
        if not parts:
            return False
        return all(_keyword_matches(text, part) for part in parts)

    pattern = _make_pattern(keyword)
    kw_starts_negated = any(keyword.startswith(neg + " ") for neg in _NEGATIONS)
    for match in pattern.finditer(text):
        if kw_starts_negated:
            return True
        if not _is_negated(text, match):
            return True
    return False


def tag_text(text: str, codebook: dict) -> list[str]:
    """
    Return list of code names that match the given text.
    Negated keyword occurrences (e.g. 'not crowded') are suppressed.
    """
    if not isinstance(text, str) or not text.strip():
        return []

    matched = []
    for code, attrs in codebook.items():
        for kw in attrs["keywords"]:
            if _keyword_matches(text, kw):
                matched.append(code)
                break
    return matched


def tag_dataframe(df: pd.DataFrame, text_col: str, codebook: dict) -> pd.DataFrame:
    """
    Add friction/nudge tag columns to a DataFrame.

    Adds:
      - one bool column per codebook code (True if matched, negation-aware)
      - 'friction_codes'  — list of matched friction code names
      - 'nudge_codes'     — list of matched nudge code names
      - 'all_codes'       — combined list

    Returns a new DataFrame (does not mutate input).
    """
    df = df.copy()

    friction_codes = [c for c, a in codebook.items() if a["type"] == "friction"]
    nudge_codes    = [c for c, a in codebook.items() if a["type"] == "nudge"]
    all_codes      = list(codebook.keys())

    for code in all_codes:
        attrs = codebook[code]
        df[code] = df[text_col].apply(
            lambda t, attrs=attrs: any(
                _keyword_matches(str(t), kw) for kw in attrs["keywords"]
            ) if isinstance(t, str) else False
        )

    df["friction_codes"] = df[friction_codes].apply(
        lambda row: [c for c in friction_codes if row[c]], axis=1
    )
    df["nudge_codes"] = df[nudge_codes].apply(
        lambda row: [c for c in nudge_codes if row[c]], axis=1
    )
    df["all_codes"] = df["friction_codes"] + df["nudge_codes"]

    return df
