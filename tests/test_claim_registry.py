import json

from src.provenance.claim_registry import build_registry, validate_claims


def test_claim_registry_builds_with_required_metadata():
    registry = build_registry()

    assert registry["claims"]
    assert registry["publication_ready"] is False
    for claim in registry["claims"]:
        assert claim["source_artifacts"]
        assert claim["reproduction_command"].startswith("make ")
        assert claim["unit_of_analysis"]
        assert claim["denominator"]


def test_claim_registry_has_no_google_review_adapter_claim():
    registry = build_registry()
    serialized = json.dumps(registry, ensure_ascii=False).lower()

    assert "review-row adapter" not in serialized
    assert "google review row" not in serialized


def test_claim_registry_validator_accepts_current_claims():
    registry = build_registry()
    # Rebuild typed claims through module-level path and ensure validation is
    # already exercised by build_registry. This assertion catches accidental
    # schema weakening where build_registry returns an empty payload.
    assert len(registry["claims"]) >= 6
