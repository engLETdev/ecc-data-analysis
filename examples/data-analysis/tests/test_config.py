"""Configuration contract: strict schema and stable path resolution."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from data_analysis.config import load_config
from data_analysis.errors import FoundationError


def test_paths_are_relative_to_config_even_from_another_directory(
    config_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)
    config = load_config(config_file)
    assert config.name == "Synthetic project"
    assert config.raw_dir == (tmp_path / "raw").resolve()
    assert config.manifest_path == (tmp_path / "state/sources.json").resolve()
    assert not config.manifest_path.parent.exists()


def test_configuration_is_immutable(config_file: Path) -> None:
    config = load_config(config_file)
    with pytest.raises(FrozenInstanceError):
        config.name = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "document",
    [
        "",
        "schema_version = 1\n",
        'schema_version = true\n[project]\nname="p"\n[storage]\nraw_dir="r"\nmanifest="m"',
        'schema_version = 2\n[project]\nname="p"\n[storage]\nraw_dir="r"\nmanifest="m"',
        'schema_version = "1"\n[project]\nname="p"\n[storage]\nraw_dir="r"\nmanifest="m"',
        'schema_version = 1\nextra=1\n[project]\nname="p"\n[storage]\nraw_dir="r"\nmanifest="m"',
        'schema_version = 1\n[project]\nname=""\n[storage]\nraw_dir="r"\nmanifest="m"',
        'schema_version = 1\n[project]\nname="  "\n[storage]\nraw_dir="r"\nmanifest="m"',
        'schema_version = 1\n[project]\nname=42\n[storage]\nraw_dir="r"\nmanifest="m"',
        'schema_version = 1\n[project]\nname="p"\nextra=1\n[storage]\nraw_dir="r"\nmanifest="m"',
        'schema_version = 1\n[project]\nname="p"\n[storage]\nraw_dir=""\nmanifest="m"',
        'schema_version = 1\n[project]\nname="p"\n[storage]\nraw_dir="r"\nmanifest=" "',
        'schema_version = 1\n[project]\nname="p"\n[storage]\nraw_dir=4\nmanifest="m"',
        'schema_version = 1\n[project]\nname="p"\n[storage]\nraw_dir="r"\nmanifest=[]',
        'schema_version = 1\n[project]\nname="p"\n[storage]\nraw_dir="r"',
        'schema_version = 1\n[project]\nname="p"\n[storage]\nraw_dir="r"\nmanifest="m"\nextra=1',
        'schema_version = 1\n[project]\nname="p"\n[storage]\nraw_dir="r"\nmanifest="r/sources.json"',
        'schema_version = 1\n[project]\nname="p"\n[storage]\nraw_dir="r"\nmanifest="r"',
        "schema_version = [invalid TOML",
    ],
)
def test_invalid_configuration_is_rejected(tmp_path: Path, document: str) -> None:
    path = tmp_path / "invalid.toml"
    path.write_text(document, encoding="utf-8")
    with pytest.raises(FoundationError):
        load_config(path)


def test_missing_configuration_reports_domain_error(tmp_path: Path) -> None:
    with pytest.raises(FoundationError):
        load_config(tmp_path / "missing.toml")


def test_absolute_storage_paths_are_supported(tmp_path: Path) -> None:
    path = tmp_path / "absolute.toml"
    path.write_text(
        f'schema_version=1\n[project]\nname="p"\n[storage]\n'
        f'raw_dir="{(tmp_path / "raw").as_posix()}"\n'
        f'manifest="{(tmp_path / "state/sources.json").as_posix()}"\n',
        encoding="utf-8",
    )
    assert load_config(path).raw_dir == tmp_path / "raw"
