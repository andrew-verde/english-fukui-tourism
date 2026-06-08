import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.analysis.keyword_cloud import (
    classify_japanese_topic_category,
    classify_review_category,
    extract_codebook_keyword_frequencies,
    extract_keyword_frequencies,
    summarize_japanese_topic_categories,
    summarize_topic_categories,
)


def test_extract_keyword_frequencies_prefers_specific_terms():
    df = pd.DataFrame(
        {
            "review_text": [
                "The dinosaur museum in Fukui was detailed, modern, and family friendly.",
                "Fukui dinosaur museum had excellent fossils and a modern layout.",
                "The cliffs at Tojinbo were dramatic and scenic at sunset.",
            ]
        }
    )

    keywords = extract_keyword_frequencies(df, top_k=8, min_frequency=1)

    assert "dinosaur museum" in keywords["term"].tolist()
    assert "museum" not in keywords["term"].tolist()


def test_classify_review_category_prefers_useful_topic_bucket():
    text = "The cliff views at Tojinbo were beautiful and perfect for photos at sunset."
    assert classify_review_category(text, "nature_scenic") == "Scenic Spots & Landscapes"


def test_summarize_topic_categories_percentages_sum_to_100():
    reviews_df = pd.DataFrame(
        {
            "review_text": [
                "The cliff views at Tojinbo were beautiful and scenic.",
                "The zen temple felt spiritual and serene.",
                "Fresh crab and soba made the food stop memorable.",
            ],
            "poi_category": ["nature_scenic", "temple_shrine", "market_shopping"],
        }
    )

    ranked = summarize_topic_categories(reviews_df, top_n=3)

    assert ranked["rank"].tolist() == [1, 2, 3]
    assert round(ranked["percentage"].sum(), 6) == 100.0


def test_extract_codebook_keyword_frequencies_adds_japanese_translations():
    texts = pd.Series(["バスの本数が少なくて混雑していた", "公共交通が少ない"])
    codebook = {
        "transport_access": {
            "label": "Transport / Access",
            "type": "friction",
            "keywords": ["バスの本数", "公共交通"],
        },
        "waiting_crowding": {
            "label": "Waiting / Crowding",
            "type": "friction",
            "keywords": ["混雑"],
        },
    }

    keywords = extract_codebook_keyword_frequencies(texts, codebook, language="ja", min_frequency=1)

    assert "バスの本数" in keywords["term"].tolist()
    row = keywords[keywords["term"] == "バスの本数"].iloc[0]
    assert row["translation"] == "bus frequency"
    assert row["display"] == "バスの本数 (bus frequency)"


def test_japanese_tourism_keywords_do_not_translate_ascii_terms():
    from src.analysis.keyword_cloud import extract_japanese_tourism_keyword_frequencies

    texts = pd.Series(["Instagramで見て、温泉と博物館に行きました。"])

    keywords = extract_japanese_tourism_keyword_frequencies(texts, min_frequency=1)

    instagram = keywords[keywords["term"] == "Instagram"].iloc[0]
    assert instagram["display"] == "Instagram"
    assert instagram["translation"] == ""


def test_japanese_topic_categories_use_english_cloud_buckets():
    texts = pd.Series(
        [
            "海の景色が美しく、自然を楽しめました。",
            "お土産と越前和紙の買い物が良かったです。",
            "駅からバスで移動しました。",
        ]
    )

    assert classify_japanese_topic_category("恐竜博物館の展示が良かった") == "Dinosaurs & Museums"
    ranked = summarize_japanese_topic_categories(texts, top_n=3)

    assert set(ranked["term"]) == {
        "Scenic Spots & Landscapes",
        "Shopping & Local Crafts",
        "Access & Visitor Logistics",
    }
