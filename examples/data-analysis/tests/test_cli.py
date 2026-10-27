"""Subprocess tests prove the user-facing commands work from another cwd."""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_cli(config_file: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    source_root = Path(__file__).resolve().parents[1] / "src"
    env = {**os.environ, "PYTHONPATH": str(source_root)}
    return subprocess.run(
        [sys.executable, "-m", "data_analysis", "--config", str(config_file), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_status_is_read_only_without_datasets(config_file: Path, tmp_path: Path) -> None:
    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    result = run_cli(config_file, tmp_path, "status")
    assert result.returncode == 0, result.stderr
    assert isinstance(json.loads(result.stdout), dict)
    assert result.stderr == ""
    assert {p.relative_to(tmp_path) for p in tmp_path.rglob("*")} == before


def test_register_source_and_repeat_via_cli(
    config_file: Path, source_file: Path, tmp_path: Path
) -> None:
    original = source_file.read_bytes()
    args = ("register-source", "--source-id", "synthetic", "--file", str(source_file))
    first = run_cli(config_file, tmp_path, *args)
    assert first.returncode == 0, first.stderr
    assert isinstance(json.loads(first.stdout), dict)
    path = tmp_path / "state/sources.json"
    first_bytes = path.read_bytes()
    second = run_cli(config_file, tmp_path, *args)
    assert second.returncode == 0, second.stderr
    assert len(json.loads(path.read_text())["sources"]) == 1
    assert path.read_bytes() == first_bytes
    assert source_file.read_bytes() == original


def test_cli_does_not_print_dataset_contents(
    config_file: Path, source_file: Path, tmp_path: Path
) -> None:
    marker = "SYNTHETIC_SECRET_DO_NOT_LOG"
    source_file.write_text(marker, encoding="utf-8")
    result = run_cli(
        config_file,
        tmp_path,
        "register-source",
        "--source-id",
        "synthetic",
        "--file",
        str(source_file),
    )
    assert result.returncode == 0, result.stderr
    assert marker not in result.stdout + result.stderr


def test_missing_source_returns_domain_error(config_file: Path, tmp_path: Path) -> None:
    result = run_cli(
        config_file,
        tmp_path,
        "register-source",
        "--source-id",
        "synthetic",
        "--file",
        str(tmp_path / "raw/missing.csv"),
    )
    assert result.returncode == 2
    assert result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "state/sources.json").exists()


def test_missing_configuration_returns_domain_error(tmp_path: Path) -> None:
    result = run_cli(tmp_path / "missing.toml", tmp_path, "status")
    assert result.returncode == 2
    assert result.stderr
    assert "Traceback" not in result.stderr


def test_deeply_nested_manifest_returns_domain_error_without_traceback(
    config_file: Path, tmp_path: Path
) -> None:
    manifest = tmp_path / "state/sources.json"
    manifest.parent.mkdir()
    document = "[" * 10_000 + "0" + "]" * 10_000
    manifest.write_text(document, encoding="utf-8")
    result = run_cli(config_file, tmp_path, "status")
    assert result.returncode == 2
    assert result.stderr
    assert "Traceback" not in result.stderr
    assert document not in result.stdout + result.stderr
    assert manifest.read_text(encoding="utf-8") == document
