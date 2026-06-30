"""
Tests for the OpenAI-backed LLM friction tagger (src/friction/llm_tagger.py).

All tests run OFFLINE: the OpenAI client is replaced by a stub, so the suite
exercises prompt construction, response parsing, failure handling, and the
DataFrame contract — never the API itself. CI must not depend on network,
billing, or model nondeterminism. Unit tests establish behavior, not
scientific tagging validity.
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.friction.llm_tagger import (
    LLMFrictionTagger,
    build_prompt,
    parse_response,
)
from src.friction.tagger import load_codebook


CODEBOOK = load_codebook()


# ── stub OpenAI client ────────────────────────────────────────────────────────

class StubClient:
    """Mimics openai.OpenAI just enough: client.chat.completions.create(...)."""

    def __init__(self, content=None, exc=None):
        self.calls = []
        self._content = content
        self._exc = exc
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc:
            raise self._exc
        msg = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def make_tagger(content=None, exc=None):
    client = StubClient(content=content, exc=exc)
    return LLMFrictionTagger(codebook=CODEBOOK, client=client), client


# ── build_prompt ──────────────────────────────────────────────────────────────

def test_prompt_contains_every_codebook_code():
    """Label space must equal the keyword tagger's (ADR 0001 comparability)."""
    prompt = build_prompt("some review", CODEBOOK)
    for code in CODEBOOK:
        assert f'"{code}"' in prompt, f"code {code} missing from prompt"


def test_prompt_excludes_keyword_lists():
    """Keywords are withheld so the LLM is an independent second instrument,
    not a paraphrase of the keyword matcher."""
    prompt = build_prompt("some review", CODEBOOK)
    # 'no public transport' is a distinctive transport_access keyword phrase.
    assert "no public transport" not in prompt


def test_prompt_embeds_tourism_text_json_escaped():
    prompt = build_prompt('tricky "quoted" text', CODEBOOK)
    assert json.dumps('tricky "quoted" text') in prompt


# ── parse_response ────────────────────────────────────────────────────────────

def test_parse_valid_response():
    content = json.dumps({"codes": ["transport_access"], "sentiment": -0.4})
    result = parse_response(content, CODEBOOK)
    assert result == {"codes": ["transport_access"], "sentiment": -0.4, "error": False}


def test_parse_strips_markdown_fences():
    inner = json.dumps({"codes": [], "sentiment": 0.9})
    result = parse_response(f"```json\n{inner}\n```", CODEBOOK)
    assert result["error"] is False
    assert result["sentiment"] == 0.9


def test_parse_drops_hallucinated_codes():
    """Codes outside the codebook must vanish, not be coerced — hallucinated
    labels would otherwise inflate friction counts."""
    content = json.dumps(
        {"codes": ["transport_access", "vibes_bad", "Type A"], "sentiment": 0.0}
    )
    result = parse_response(content, CODEBOOK)
    assert result["codes"] == ["transport_access"]
    assert result["error"] is False


def test_parse_preserves_codebook_order():
    codes = list(CODEBOOK)[:3]
    content = json.dumps({"codes": list(reversed(codes)), "sentiment": 0.0})
    assert parse_response(content, CODEBOOK)["codes"] == codes


@pytest.mark.parametrize("bad", [
    "",                                     # empty
    "Sure! Here is the JSON you asked for", # prose, no JSON
    "{not json",                            # malformed
    json.dumps(["transport_access"]),       # list, not object
    json.dumps({"codes": "transport_access", "sentiment": 0}),  # codes not list
    json.dumps({"codes": []}),              # sentiment missing
    json.dumps({"codes": [], "sentiment": "negative"}),         # non-numeric
    json.dumps({"codes": [], "sentiment": 3.5}),                # out of range
])
def test_parse_failures_flag_error(bad):
    """Every malformed shape maps to the same safe error result: no codes,
    NaN sentiment, error=True — so failed rows can be excluded downstream
    instead of silently counting as 'no friction'."""
    result = parse_response(bad, CODEBOOK)
    assert result["codes"] == []
    assert result["sentiment"] != result["sentiment"]  # NaN
    assert result["error"] is True


# ── tag_text ──────────────────────────────────────────────────────────────────

def test_tag_text_happy_path_and_request_shape():
    tagger, client = make_tagger(
        content=json.dumps({"codes": ["price_value"], "sentiment": -0.2})
    )
    result = tagger.tag_text("Entry fee felt overpriced for what you get.")
    assert result["codes"] == ["price_value"]
    call = client.calls[0]
    assert call["temperature"] == 0
    assert call["messages"][0]["role"] == "system"


def test_tag_text_blank_input_is_no_codes_not_error():
    """Matches keyword-tagger semantics: nothing to classify ≠ failure."""
    tagger, client = make_tagger()
    for blank in ("", "   ", None, 42):
        result = tagger.tag_text(blank)
        assert result == {"codes": [], "sentiment": result["sentiment"], "error": False}
        assert result["sentiment"] != result["sentiment"]  # NaN
    assert client.calls == []  # no API spend on blanks


def test_tag_text_api_exception_flags_error():
    tagger, _ = make_tagger(exc=RuntimeError("rate limited"))
    result = tagger.tag_text("some review")
    assert result["codes"] == []
    assert result["error"] is True


# ── tag_dataframe contract ────────────────────────────────────────────────────

def test_tag_dataframe_matches_keyword_tagger_schema():
    """Output must be engine-interchangeable with tagger.tag_dataframe:
    one bool column per code + friction_codes/nudge_codes/all_codes, plus
    the LLM-only llm_sentiment / llm_error columns."""
    tagger, _ = make_tagger(
        content=json.dumps(
            {"codes": ["transport_access", "scenic_value"], "sentiment": 0.5}
        )
    )
    df = pd.DataFrame({"review_text": ["a", "b"]})
    out = tagger.tag_dataframe(df, text_col="review_text")

    for code in CODEBOOK:
        assert code in out.columns
        assert out[code].dtype == bool
    assert out["transport_access"].all()

    assert out["friction_codes"].tolist() == [["transport_access"]] * 2
    assert out["nudge_codes"].tolist() == [["scenic_value"]] * 2
    assert out["all_codes"].tolist() == [["transport_access", "scenic_value"]] * 2
    assert (out["llm_sentiment"] == 0.5).all()
    assert not out["llm_error"].any()
    # input must not be mutated
    assert list(df.columns) == ["review_text"]


def test_tag_dataframe_error_rows_are_flagged():
    tagger, _ = make_tagger(content="not json at all")
    df = pd.DataFrame({"review_text": ["a"]})
    out = tagger.tag_dataframe(df, text_col="review_text")
    assert out["llm_error"].all()
    assert not out[list(CODEBOOK)].any(axis=None)
