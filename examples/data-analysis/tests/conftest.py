"""Isolated synthetic inputs for the data-analysis foundation."""

from pathlib import Path

import pytest


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    config_dir = tmp_path / "settings"
    config_dir.mkdir()
    path = config_dir / "project.toml"
    path.write_text(
        "schema_version = 1\n"
        '[project]\nname = "Synthetic project"\n'
        '[storage]\nraw_dir = "../raw"\n'
        'manifest = "../state/sources.json"\n',
        encoding="utf-8",
    )
    return path


@pytest.fixture
def source_file(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "synthetic.csv"
    path.write_bytes(b"date,value\n2026-01-01,3\n")
    return path
