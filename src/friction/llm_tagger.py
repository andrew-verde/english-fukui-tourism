"""
llm_tagger.py — OpenAI-backed friction/nudge tagger and sentiment scorer.

ROLE IN THE RESEARCH DESIGN (ADR 0001, decision 4)
--------------------------------------------------
The keyword tagger (src/friction/tagger.py) remains the primary instrument:
it is deterministic and auditable. This module is an optional comparator
using the same codebook. No headline result may depend on LLM tags alone.

This supersedes the retired ad-hoc OpenAI analysis (src/analysis/ai_insights.py,
removed at commit 7c1557d), which used a pre-codebook Type A/B/C taxonomy.
The LLM now emits the same code names
as config/friction_codebook.yaml, so both taggers produce identical DataFrame
contracts (one bool column per code + friction_codes / nudge_codes / all_codes)
and are interchangeable inputs to the evaluation pipeline.

SENTIMENT
---------
The LLM also returns a companion sentiment score in [-1, 1]
(`llm_sentiment`).

RELIABILITY HANDLING
--------------------
LLM output is not deterministic and can be malformed. Design choices:
  - temperature=0 to minimise (not eliminate) run-to-run variance;
  - strict JSON parsing with code-fence stripping;
  - code names not present in the codebook are silently DROPPED, never
    coerced to a near-match — hallucinated codes must not inflate counts;
  - any parse/API failure yields zero codes, NaN sentiment, and
    llm_error=True so failed rows can be excluded from evaluation rather
    than counted as "no friction" (which would bias recall upward for the
    keyword tagger in the comparison).
"""

import json
import os
import time
from pathlib import Path

import pandas as pd

from src.friction.tagger import load_codebook
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = (
    "You are a research assistant applying a fixed qualitative codebook to "
    "tourism text for Fukui Prefecture, Japan. You return only valid "
    "JSON, no prose, no markdown."
)

_ERROR_RESULT = {"codes": [], "sentiment": float("nan"), "error": True}


def build_prompt(text: str, codebook: dict) -> str:
    """Render the tagging prompt for one text record.

    The full codebook (code name, human label, type) is embedded verbatim so
    the LLM's label space is exactly the keyword tagger's label space — the
    comparability requirement of ADR 0001. Definitions come from the labels
    only; keyword lists are deliberately NOT shown, otherwise the LLM would
    partially replicate the keyword instrument instead of providing an
    independent second judgment.
    """
    code_lines = "\n".join(
        f'- "{code}" ({attrs["type"]}): {attrs["label"]}'
        for code, attrs in codebook.items()
    )
    return f"""Apply this codebook to the tourism text below.

Codebook (use these exact code names, nothing else):
{code_lines}

Rules:
- A code applies only if the text clearly expresses it; do not infer from absence.
- Multiple codes may apply; an empty list is a valid answer.
- Negated friction ("not crowded", "wasn't busy") is NOT friction.
- "sentiment" is the overall tone of the text, a number from -1 (very negative) to 1 (very positive).

Return a JSON object with exactly these fields:
{{"codes": [<code names>], "sentiment": <number>}}

Tourism text: {json.dumps(text)}"""


def parse_response(content: str, codebook: dict) -> dict:
    """Parse one LLM response into {codes, sentiment, error}.

    Pure function (no I/O) so the failure modes are unit-testable without a
    network: code fences, malformed JSON, wrong types, hallucinated code
    names, out-of-range sentiment.
    """
    if not isinstance(content, str) or not content.strip():
        return dict(_ERROR_RESULT)

    cleaned = content.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` fences some models add despite instructions.
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else ""
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    cleaned = cleaned.strip()

    try:
        obj = json.loads(cleaned)
        if not isinstance(obj, dict):
            raise ValueError("response is not a JSON object")
        raw_codes = obj.get("codes", [])
        if not isinstance(raw_codes, list):
            raise ValueError("'codes' is not a list")
        # Drop hallucinated codes rather than fuzzy-matching them; preserve
        # codebook order for deterministic output.
        valid = set(raw_codes)
        codes = [c for c in codebook if c in valid]

        sentiment = float(obj["sentiment"])
        if not (-1.0 <= sentiment <= 1.0):
            raise ValueError(f"sentiment {sentiment} outside [-1, 1]")
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
        logger.error(f"Unparseable LLM response ({e}): {content[:200]!r}")
        return dict(_ERROR_RESULT)

    return {"codes": codes, "sentiment": sentiment, "error": False}


class LLMFrictionTagger:
    """Applies the friction codebook to text via the OpenAI chat API."""

    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None,
                 codebook: dict | None = None, client=None):
        self.model = model
        self.codebook = codebook if codebook is not None else load_codebook()
        if client is not None:
            # Injection point for tests and for swapping providers.
            self.client = client
        else:
            from openai import OpenAI  # imported lazily; not a core dependency

            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set (see .env)")
            self.client = OpenAI(api_key=api_key)

    def tag_text(self, text: str) -> dict:
        """Tag one text; returns {codes, sentiment, error}."""
        if not isinstance(text, str) or not text.strip():
            # Match keyword tagger semantics: blank input is no-codes, but it
            # is not an error — there was nothing to classify.
            return {"codes": [], "sentiment": float("nan"), "error": False}
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": build_prompt(text, self.codebook)},
                ],
                temperature=0,
                max_tokens=300,
            )
            content = response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return dict(_ERROR_RESULT)
        return parse_response(content, self.codebook)

    def tag_dataframe(self, df: pd.DataFrame, text_col: str,
                      delay: float = 0.0) -> pd.DataFrame:
        """Tag every row; output schema mirrors tagger.tag_dataframe.

        Adds the same columns as the keyword path (one bool per code,
        friction_codes / nudge_codes / all_codes) plus llm_sentiment and
        llm_error, so downstream evaluation code is engine-agnostic.
        Returns a new DataFrame (does not mutate input).
        """
        df = df.copy()
        friction_codes = [c for c, a in self.codebook.items() if a["type"] == "friction"]
        nudge_codes    = [c for c, a in self.codebook.items() if a["type"] == "nudge"]

        results = []
        for i, text in enumerate(df[text_col]):
            results.append(self.tag_text(text))
            if delay and i < len(df) - 1:
                time.sleep(delay)

        for code in self.codebook:
            df[code] = [code in r["codes"] for r in results]
        df["friction_codes"] = [[c for c in r["codes"] if c in friction_codes] for r in results]
        df["nudge_codes"]    = [[c for c in r["codes"] if c in nudge_codes] for r in results]
        df["all_codes"]      = df["friction_codes"] + df["nudge_codes"]
        df["llm_sentiment"]  = [r["sentiment"] for r in results]
        df["llm_error"]      = [r["error"] for r in results]
        return df
