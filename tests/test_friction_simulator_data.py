import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_friction_simulator_data import build_payload


def test_friction_simulator_payload_has_claim_boundary_and_sources():
    payload = build_payload()

    assert payload["schema_version"] == 1
    assert "not causal impact" in payload["interpretation"]["claim_boundary"]
    assert "opportunity-gap forecasts" in payload["interpretation"]["claim_boundary"]
    assert payload["sem"]["stage1"]["satisfaction_to_intention_std"] > 0
    assert payload["sem"]["friction_codes"]

    first = payload["sem"]["friction_codes"][0]
    assert {
        "code",
        "label",
        "sem_path_to_satisfaction_std",
        "prevalence_among_reporters",
        "recoverable_intention_ceiling",
    }.issubset(first)

    repos = {source["repo"] for source in payload["public_sources"]}
    assert "https://github.com/code4fukui/fukui-kanko-survey" in repos
    assert "https://github.com/amilkh/hokuriku-tourism-ai-governance" in repos
