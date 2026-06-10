import json
from pathlib import Path


CONFIG = Path(__file__).resolve().parent.parent / "experiments" / "nudge-pilot" / "study-config.json"


def test_nudge_pilot_config_has_sem_constructs():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    construct_ids = {construct["id"] for construct in config["constructs"]}

    assert {
        "information_clarity",
        "perceived_friction",
        "planning_confidence",
        "visit_intention",
        "information_trust",
    }.issubset(construct_ids)

    for construct in config["constructs"]:
        assert len(construct["items"]) >= 3


def test_nudge_pilot_conditions_match_task_nudges():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    condition_ids = {condition["id"] for condition in config["conditions"]}

    assert {"control", "combined"}.issubset(condition_ids)

    nudge_conditions = condition_ids - {"control", "combined"}
    for task in config["tasks"]:
        assert nudge_conditions.issubset(set(task["nudges"]))
        assert task["accuracy_question"]["correct"] in task["accuracy_question"]["options"]
        assert len(task["decision_options"]) >= 3


def test_nudge_pilot_avoids_direct_identifiers():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    background_ids = {question["id"] for question in config["background_questions"]}

    assert "name" not in background_ids
    assert "email" not in background_ids
    assert "phone" not in background_ids
