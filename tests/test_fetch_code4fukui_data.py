import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.fetch_code4fukui_data import _raw_github_url, _row_count, _validate_source


PINNED = {
    "upstream_repo": "https://github.com/example/data",
    "commit": "a" * 40,
    "source_path": "all.csv",
    "sha256": "b" * 64,
    "filename": "data.csv",
}


def test_raw_url_is_immutable():
    assert _raw_github_url(
        PINNED["upstream_repo"], PINNED["commit"], PINNED["source_path"]
    ) == f"https://raw.githubusercontent.com/example/data/{'a' * 40}/all.csv"


def test_source_requires_full_commit_and_checksum():
    _validate_source("data", PINNED)
    with pytest.raises(ValueError, match="full 40-character"):
        _validate_source("data", {**PINNED, "commit": "main"})
    with pytest.raises(ValueError, match="64-character"):
        _validate_source("data", {**PINNED, "sha256": "unknown"})


def test_csv_row_count_handles_quoted_newlines_and_bom():
    data = '\ufeffid,text\n1,"two\nlines"\n2,plain\n'.encode()
    assert _row_count(data) == 2
