import pytest

from src.analysis.topic_modeling import assign_primary_theme


def test_theme_generic_museum_not_dinosaur():
    text = "This is a great museum with interesting exhibits and exhibitions."
    assert assign_primary_theme(text) != "Dinosaur"


def test_theme_dinosaur_signals_match_dinosaur():
    text = "The dinosaur fossils and paleontology displays were impressive."
    assert assign_primary_theme(text) == "Dinosaur"

