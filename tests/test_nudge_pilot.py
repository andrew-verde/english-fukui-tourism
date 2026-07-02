import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_study_config_contract():
    path = ROOT / "experiments" / "nudge-pilot" / "study-config.json"
    config = json.loads(path.read_text(encoding="utf-8"))

    assert len(config["conditions"]) == 5
    assert len(config["tasks"]) == 3
    expected_arms = {
        "transport_access",
        "opening_hours_availability",
        "itinerary_fit_time_cost",
    }
    for task in config["tasks"]:
        assert set(task["nudges"]) == expected_arms
        assert len(task["decision_options"]) == 3
        assert task["accuracy_question"]["correct"] in task["accuracy_question"]["options"]


def test_power_calculations():
    path = ROOT / "scripts" / "nudge_pilot_power.py"
    spec = importlib.util.spec_from_file_location("nudge_pilot_power", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert module.n_per_arm(0.25) == 252
    assert module.n_per_arm(0.125) == 1005
    assert module.n_per_arm(0.10) == 1570
    assert module.d_plan(0.18, 0.06) == 0.12
