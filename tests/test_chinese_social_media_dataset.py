import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_chinese_social_media_dataset import (
    build_chinese_social_outputs,
    normalize_social_csv,
)


def test_chinese_social_builder_handles_schema_only_csv(tmp_path):
    xhs = tmp_path / "fukui_xhs_reviews.csv"
    xhs.write_text("note_id,title,note_url,author,author_url\n", encoding="utf-8")

    report = build_chinese_social_outputs(
        input_dir=tmp_path,
        output_dir=tmp_path / "out",
        input_files=[xhs],
        review_friction_path=tmp_path / "missing_review_friction.csv",
    )

    assert report["input_files_discovered"] == 1
    assert report["rows_retained"] == 0
    assert (tmp_path / "out" / "chinese_social_posts.csv").exists()
    assert (tmp_path / "out" / "chinese_social_readiness.md").exists()


def test_normalize_social_csv_maps_xhs_schema_to_review_like_rows(tmp_path):
    xhs = tmp_path / "fukui_xhs_reviews.csv"
    xhs.write_text(
        "note_id,title,note_url,author,author_url\n"
        "n1,福井交通不便 但是东寻坊很美,https://xhs.example/n1,旅行者,https://xhs.example/u1\n",
        encoding="utf-8",
    )

    df = normalize_social_csv(xhs)

    assert len(df) == 1
    assert df.loc[0, "city"] == "Fukui"
    assert df.loc[0, "source_platform"] == "xiaohongshu"
    assert df.loc[0, "text_content"] == "福井交通不便 但是东寻坊很美"
    assert df.loc[0, "content_language"] == "zh"
    assert 0 <= df.loc[0, "sentiment_norm"] <= 1


def test_chinese_social_builder_tags_and_compares_populated_rows(tmp_path):
    xhs = tmp_path / "fukui_xhs_reviews.csv"
    xhs.write_text(
        "note_id,title,note_url,author,author_url\n"
        "n1,福井交通不便 公交班次少,https://xhs.example/n1,a,\n"
        "n2,东寻坊很美 推荐,https://xhs.example/n2,b,\n",
        encoding="utf-8",
    )
    douyin = tmp_path / "kanazawa_douyin_reviews.csv"
    douyin.write_text(
        "video_id,title,video_url,author\n"
        "v1,金泽交通便利 但门票贵,https://dy.example/v1,c\n",
        encoding="utf-8",
    )
    review_friction = tmp_path / "friction_by_city_language_group.csv"
    review_friction.write_text(
        "city,language_group,code,label,count,denominator_reviews,pct_reviews\n"
        "Fukui,english,transport_access,Transport / Access,1,10,10.0\n",
        encoding="utf-8",
    )

    report = build_chinese_social_outputs(
        input_dir=tmp_path,
        output_dir=tmp_path / "out",
        input_files=[xhs, douyin],
        review_friction_path=review_friction,
    )

    assert report["rows_retained"] == 3

    tagged = pd.read_csv(tmp_path / "out" / "tagged_chinese_social_posts.csv")
    fukui = tagged[tagged["city"] == "Fukui"].iloc[0]
    assert bool(fukui["transport_access"]) is True
    assert bool(fukui["any_friction"]) is True

    friction = pd.read_csv(tmp_path / "out" / "chinese_friction_by_city_platform.csv")
    row = friction[
        (friction["city"] == "Fukui")
        & (friction["source_platform"] == "xiaohongshu")
        & (friction["friction_code"] == "transport_access")
    ].iloc[0]
    assert row["count"] == 1
    assert row["denominator_posts"] == 2

    comparison = pd.read_csv(tmp_path / "out" / "chinese_vs_review_language_friction_comparison.csv")
    assert comparison.loc[0, "comparison_group"] == "google_english"
