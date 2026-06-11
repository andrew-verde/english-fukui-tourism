"""
tagger.py — Apply friction/nudge codebook to review or mention text.

DESIGN RATIONALE: KEYWORD MATCHING, NOT ML
------------------------------------------
This module deliberately implements friction (フリクション / 摩擦) tagging as
transparent, rule-based keyword matching rather than a trained classifier.
The trade-off is explicit:

  - Precision/recall: a supervised or LLM classifier would likely achieve
    higher recall (paraphrases, misspellings, implicit complaints) and
    possibly higher precision. Keyword rules miss anything not in the
    codebook vocabulary and can fire on figurative usage.
  - Traceability: every single tag produced here can be traced to a specific
    keyword line in config/friction_codebook.yaml and reproduced exactly —
    the system is deterministic, auditable, and explainable to a thesis
    examiner with no model weights, prompts, or training-data provenance to
    defend. For an academic instrument this auditability was judged to
    outweigh the recall ceiling.

Crucially, the tagger's accuracy is NOT assumed: it is empirically evaluated
against a blind, double-coded human gold standard (see
scripts/build_gold_set.py and scripts/evaluate_gold_set.py), and the measured
per-code precision/recall bound every downstream result (SEM Stage 2,
prefecture comparisons, nudge ranking).

MATCHING RULES
--------------
Codebook is loaded from config/friction_codebook.yaml.
Keyword matching uses word-boundary regex (case-insensitive), so 'bus' does
not fire inside 'business'. Multi-word phrases are matched as-is (spaces
preserved).

Compound keywords: a keyword containing '&&' (e.g. 'stairs && steep')
requires ALL of its sub-keywords to appear somewhere in the text
(co-occurrence, any order/distance). This lets the codebook use broad,
high-recall words while recovering precision through required co-occurrence.

Negation handling (negation-aware matching): if a negation word (not, less,
never, wasn't, etc.) appears within a 4-word lookbehind window before a
keyword match, the match is suppressed. This matters for English reviews,
where praise is routinely phrased through negated friction vocabulary —
"not crowded at all", "wasn't busy", "less crowded than Kyoto" — which a
naive keyword matcher would mis-tag as waiting_crowding friction. Keywords
that themselves BEGIN with a negation word ('no food', 'not worth') encode
the negation intentionally and bypass the lookbehind check.
"""

import re
from pathlib import Path

import pandas as pd
import yaml

# Words that, when appearing within _LOOKBEHIND_N words before a matched
# keyword, indicate the keyword is negated and should NOT count as a friction
# signal. The set covers explicit negators (not/no/never), contracted
# auxiliaries (wasn't/didn't/can't...), quantity-reducers (less/fewer), and
# approximate negators (hardly/barely/rarely/seldom) — all of which flip a
# friction keyword into praise or neutrality in review English
# ("hardly any queue", "less crowded", "didn't wait").
_NEGATIONS = {
    "not", "no", "never", "less", "fewer", "neither", "nor",
    "wasn't", "weren't", "isn't", "aren't", "won't", "wouldn't",
    "doesn't", "don't", "didn't", "couldn't", "can't", "cannot",
    "without", "hardly", "barely", "rarely", "seldom",
}

# Size of the negation lookbehind window, in WORDS (not characters). 4 words
# accommodates intervening adverbs/intensifiers ("not really all that
# crowded") while staying short enough that a negation in a *previous clause*
# does not wrongly suppress a genuine friction mention later in the sentence.
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
    """Map curly/backtick apostrophes to the ASCII apostrophe.

    Review text scraped from the web frequently uses typographic quotes
    (e.g. "wasn’t" with U+2019). Without normalization, contracted negators
    like wasn't/didn't would fail to match the ASCII forms in _NEGATIONS and
    negated friction would slip through as false positives.
    """
    return text.replace("’", "'").replace("‘", "'").replace("`", "'")


def _make_pattern(keyword: str) -> re.Pattern:
    """Compile a case-insensitive, word-boundary-anchored pattern.

    \\b anchors prevent substring fires ('bus' inside 'business', 'wait'
    inside 'waiter' is still matched since \\b allows it only at word edges);
    re.escape makes keyword text literal so codebook entries containing
    regex metacharacters cannot alter matching semantics.
    """
    return re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)


def _is_negated(text: str, match: re.Match) -> bool:
    """
    Return True if a negation word appears within _LOOKBEHIND_N words
    immediately before the match start position.

    Implementation: take the text before the match, tokenize into words
    (apostrophes kept inside tokens so "wasn't" survives as one word), keep
    only the last _LOOKBEHIND_N tokens, and test membership in _NEGATIONS.
    Note the window is purely positional — it does not respect clause or
    sentence boundaries — which is a deliberate simplicity/precision
    trade-off documented in the module docstring and stress-tested via the
    gold-set evaluation.
    """
    before = text[:match.start()]
    words_before = re.findall(r"\b[\w']+\b", before)[-_LOOKBEHIND_N:]
    return any(w.lower() in _NEGATIONS for w in words_before)


def _keyword_matches(text: str, keyword: str) -> bool:
    """
    Return True if keyword matches in text and is NOT preceded by a negation.

    Compound keywords ('&&' co-occurrence operator):
      - If keyword contains '&&', all sub-keywords must match somewhere in
        text (each independently negation-checked, any order, any distance).
        Rationale: a single broad word like 'stairs' or 'busy' would be
        high-recall but low-precision; requiring co-occurrence ('stairs &&
        steep', 'busy && too') recovers precision while keeping the
        individual words broad. This is the codebook's only composition
        mechanism, kept minimal on purpose so every rule stays auditable.

    Keywords that begin with a negation word (e.g. 'no food', 'not worth',
    'nowhere to eat') encode negation explicitly — the negation IS the
    friction signal, so the lookbehind suppression is skipped for them.
    All other keywords (single- or multi-word) are subject to negation checking,
    so 'not too crowded' does not match 'too crowded'.

    Every occurrence of the keyword is examined (finditer): one negated
    occurrence does not veto a later non-negated occurrence elsewhere in the
    same text.
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

    A code is assigned if ANY of its keywords matches (logical OR across the
    code's keyword list); the inner break stops at the first hit since one
    match suffices. Codes are multi-label: a single review can legitimately
    carry several friction codes. Non-string / blank input yields no codes.
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

    The per-code boolean columns are what the gold-set kit
    (scripts/build_gold_set.py) samples from and what the evaluation
    (scripts/evaluate_gold_set.py) scores, so this function is the single
    point where machine labels enter the analysis pipeline — its determinism
    (same text + same codebook → same tags, no randomness, no model state)
    is what makes the whole friction analysis reproducible.

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
