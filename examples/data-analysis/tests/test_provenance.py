"""Identity, immutable originals, idempotence and fail-closed manifests."""

import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import data_analysis.provenance as provenance
from data_analysis.config import load_config
from data_analysis.errors import FoundationError
from data_analysis.manifest import load_manifest
from data_analysis.provenance import fingerprint_file, register_source

ECC_COMMIT = "25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b"


def test_fingerprint_matches_original_bytes(source_file: Path) -> None:
    original = source_file.read_bytes()
    result = fingerprint_file(source_file)
    assert result.sha256 == hashlib.sha256(original).hexdigest()
    assert result.size_bytes == len(original)
    assert source_file.read_bytes() == original
    with pytest.raises(FrozenInstanceError):
        result.size_bytes = 0  # type: ignore[misc]


def test_empty_source_has_valid_identity(tmp_path: Path) -> None:
    path = tmp_path / "empty"
    path.touch()
    result = fingerprint_file(path)
    assert result.size_bytes == 0
    assert result.sha256 == hashlib.sha256(b"").hexdigest()


@pytest.mark.parametrize("name", ["missing", "."])
def test_fingerprint_rejects_non_files(tmp_path: Path, name: str) -> None:
    with pytest.raises(FoundationError):
        fingerprint_file(tmp_path / name)


def test_file_changed_during_hash_is_rejected(
    source_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_open = Path.open

    class ChangingReader:
        def __init__(self, handle):
            self.handle = handle
            self.changed = False

        def __enter__(self):
            self.handle.__enter__()
            return self

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.handle, name)

        def read(self, *args):
            content = self.handle.read(*args)
            if content and not self.changed:
                with original_open(source_file, "ab") as writer:
                    writer.write(b"changed-during-reading")
                self.changed = True
            return content

    def changing_open(path: Path, mode="r", *args, **kwargs):
        handle = original_open(path, mode, *args, **kwargs)
        return ChangingReader(handle) if path == source_file and mode == "rb" else handle

    monkeypatch.setattr(Path, "open", changing_open)
    with pytest.raises(FoundationError):
        fingerprint_file(source_file)


def test_registration_is_idempotent_and_preserves_the_original(
    config_file: Path, source_file: Path
) -> None:
    config = load_config(config_file)
    original = source_file.read_bytes()
    first = register_source(config, "synthetic", source_file)
    saved = config.manifest_path.read_bytes()
    second = register_source(config, "synthetic", source_file)
    assert first.created is True
    assert second.created is False
    assert second.record == first.record
    assert config.manifest_path.read_bytes() == saved
    assert source_file.read_bytes() == original
    manifest = load_manifest(config.manifest_path)
    assert manifest.records == (first.record,)
    assert first.record.relative_path == "synthetic.csv"
    assert first.record.source_id == "synthetic"
    assert first.record.sha256 == hashlib.sha256(original).hexdigest()
    assert first.record.size_bytes == len(original)
    assert first.record.registered_at
    with pytest.raises(FrozenInstanceError):
        first.record.source_id = "changed"  # type: ignore[misc]


def test_new_content_creates_a_new_source_version(config_file: Path, source_file: Path) -> None:
    config = load_config(config_file)
    first = register_source(config, "synthetic", source_file)
    source_file.write_bytes(b"changed synthetic content")
    second = register_source(config, "synthetic", source_file)
    assert second.created is True
    assert second.record.sha256 != first.record.sha256
    assert len(load_manifest(config.manifest_path).records) == 2


def test_identical_bytes_with_different_logical_ids_remain_distinct(
    config_file: Path, source_file: Path
) -> None:
    config = load_config(config_file)
    first = register_source(config, "source-a", source_file)
    second = register_source(config, "source-b", source_file)
    assert first.created is second.created is True
    assert first.record.sha256 == second.record.sha256
    assert len(load_manifest(config.manifest_path).records) == 2


def test_relocated_identical_content_keeps_first_registration(
    config_file: Path, source_file: Path
) -> None:
    config = load_config(config_file)
    first = register_source(config, "same-source", source_file)
    other = source_file.with_name("renamed.csv")
    other.write_bytes(source_file.read_bytes())
    second = register_source(config, "same-source", other)
    assert second.created is False
    assert second.record == first.record


def test_manifest_records_pinned_ecc_without_source_content(
    config_file: Path, source_file: Path
) -> None:
    secret_marker = "SYNTHETIC_SECRET_DO_NOT_EMIT"
    source_file.write_text(secret_marker, encoding="utf-8")
    config = load_config(config_file)
    register_source(config, "synthetic", source_file)
    raw = config.manifest_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data["schema_version"] == 1
    assert data["ecc_commit"] == ECC_COMMIT
    assert len(data["sources"]) == 1
    assert secret_marker not in raw
    assert str(source_file.resolve()) not in raw


@pytest.mark.parametrize("source_id", ["", " ", "../escape", "-bad", "área", "a b", "x" * 65])
def test_invalid_logical_id_is_rejected_without_writing(
    config_file: Path, source_file: Path, source_id: str
) -> None:
    config = load_config(config_file)
    with pytest.raises(FoundationError):
        register_source(config, source_id, source_file)
    assert not config.manifest_path.exists()


def test_source_outside_raw_directory_is_rejected(config_file: Path, tmp_path: Path) -> None:
    config = load_config(config_file)
    outside = tmp_path / "outside.csv"
    outside.write_text("synthetic", encoding="utf-8")
    with pytest.raises(FoundationError):
        register_source(config, "outside", outside)
    assert not config.manifest_path.exists()


def test_symlink_cannot_escape_raw_directory(
    config_file: Path, source_file: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside.csv"
    outside.write_text("synthetic", encoding="utf-8")
    symlink = source_file.with_name("alias.csv")
    try:
        symlink.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks is unavailable on this platform")
    config = load_config(config_file)
    with pytest.raises(FoundationError):
        register_source(config, "alias", symlink)


def test_source_swapped_to_external_symlink_after_resolution_is_rejected(
    config_file: Path,
    source_file: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_config(config_file)
    outside = tmp_path / "external.csv"
    outside.write_bytes(b"external synthetic bytes")
    original_bytes = source_file.read_bytes()
    preserved = source_file.with_name("preserved-original.csv")
    original_fingerprint = provenance.fingerprint_file

    def swap_before_fingerprint(path: Path):
        source_file.rename(preserved)
        source_file.symlink_to(outside)
        return original_fingerprint(path)

    monkeypatch.setattr(provenance, "fingerprint_file", swap_before_fingerprint)
    with pytest.raises(FoundationError):
        register_source(config, "synthetic", source_file)
    assert not config.manifest_path.exists()
    assert preserved.read_bytes() == original_bytes
    assert outside.read_bytes() == b"external synthetic bytes"


def test_source_swapped_to_external_symlink_after_hash_is_rejected(
    config_file: Path,
    source_file: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_config(config_file)
    outside = tmp_path / "external-after-hash.csv"
    outside.write_bytes(b"external synthetic bytes")
    original_bytes = source_file.read_bytes()
    preserved = source_file.with_name("preserved-after-hash.csv")
    original_fingerprint = provenance.fingerprint_file

    def swap_after_fingerprint(path: Path):
        result = original_fingerprint(path)
        source_file.rename(preserved)
        source_file.symlink_to(outside)
        return result

    monkeypatch.setattr(provenance, "fingerprint_file", swap_after_fingerprint)
    with pytest.raises(FoundationError):
        register_source(config, "synthetic", source_file)
    assert not config.manifest_path.exists()
    assert preserved.read_bytes() == original_bytes
    assert outside.read_bytes() == b"external synthetic bytes"


def test_parent_directory_swapped_to_external_symlink_is_rejected(
    config_file: Path,
    source_file: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_config(config_file)
    nested = source_file.parent / "nested"
    nested.mkdir()
    source = nested / "data.csv"
    source.write_bytes(b"original synthetic bytes")
    outside_dir = tmp_path / "external-directory"
    outside_dir.mkdir()
    outside = outside_dir / "data.csv"
    outside.write_bytes(b"external synthetic bytes")
    preserved_dir = source_file.parent / "preserved-directory"
    original_fingerprint = provenance.fingerprint_file

    def swap_parent_before_fingerprint(path: Path):
        nested.rename(preserved_dir)
        nested.symlink_to(outside_dir, target_is_directory=True)
        return original_fingerprint(path)

    monkeypatch.setattr(provenance, "fingerprint_file", swap_parent_before_fingerprint)
    with pytest.raises(FoundationError):
        register_source(config, "synthetic", source)
    assert not config.manifest_path.exists()
    assert (preserved_dir / "data.csv").read_bytes() == b"original synthetic bytes"
    assert outside.read_bytes() == b"external synthetic bytes"


def test_missing_manifest_is_read_only_and_empty(tmp_path: Path) -> None:
    path = tmp_path / "not-created/sources.json"
    manifest = load_manifest(path)
    assert manifest.records == ()
    assert not path.parent.exists()


def _valid_manifest() -> dict:
    return {
        "schema_version": 1,
        "ecc_commit": ECC_COMMIT,
        "sources": [
            {
                "source_id": "synthetic",
                "relative_path": "synthetic.csv",
                "sha256": "a" * 64,
                "size_bytes": 10,
                "registered_at": "2026-10-26T12:00:00Z",
            }
        ],
    }


@pytest.mark.parametrize(
    "document",
    [
        "not valid json",
        "[]",
        "null",
        json.dumps({**_valid_manifest(), "schema_version": True}),
        json.dumps({**_valid_manifest(), "schema_version": 2}),
        json.dumps({**_valid_manifest(), "ecc_commit": "unknown"}),
        json.dumps({**_valid_manifest(), "unexpected": 1}),
        json.dumps({**_valid_manifest(), "sources": {}}),
        json.dumps({**_valid_manifest(), "sources": [None]}),
        json.dumps(
            {
                **_valid_manifest(),
                "sources": [{**_valid_manifest()["sources"][0], "size_bytes": True}],
            }
        ),
        json.dumps(
            {
                **_valid_manifest(),
                "sources": [{**_valid_manifest()["sources"][0], "size_bytes": -1}],
            }
        ),
        json.dumps(
            {
                **_valid_manifest(),
                "sources": [{**_valid_manifest()["sources"][0], "sha256": "not-a-hash"}],
            }
        ),
        json.dumps(
            {
                **_valid_manifest(),
                "sources": [
                    {
                        **_valid_manifest()["sources"][0],
                        "relative_path": "../escape.csv",
                    }
                ],
            }
        ),
        json.dumps(
            {
                **_valid_manifest(),
                "sources": [{**_valid_manifest()["sources"][0], "registered_at": "not-a-time"}],
            }
        ),
        json.dumps(
            {
                **_valid_manifest(),
                "sources": [{**_valid_manifest()["sources"][0], "unexpected": 1}],
            }
        ),
        json.dumps({**_valid_manifest(), "sources": _valid_manifest()["sources"] * 2}),
    ],
)
def test_invalid_manifest_is_rejected_without_replacement(
    config_file: Path, source_file: Path, document: str
) -> None:
    config = load_config(config_file)
    config.manifest_path.parent.mkdir(parents=True)
    config.manifest_path.write_text(document, encoding="utf-8")
    with pytest.raises(FoundationError):
        register_source(config, "synthetic", source_file)
    assert config.manifest_path.read_text(encoding="utf-8") == document


def test_existing_writer_lock_is_respected(config_file: Path, source_file: Path) -> None:
    config = load_config(config_file)
    config.manifest_path.parent.mkdir(parents=True)
    lock = config.manifest_path.with_name(config.manifest_path.name + ".lock")
    lock.write_text("another writer", encoding="utf-8")
    with pytest.raises(FoundationError):
        register_source(config, "synthetic", source_file)
    assert lock.read_text(encoding="utf-8") == "another writer"
    assert not config.manifest_path.exists()


def test_successful_registration_cleans_its_lock(config_file: Path, source_file: Path) -> None:
    config = load_config(config_file)
    register_source(config, "synthetic", source_file)
    assert not config.manifest_path.with_name(config.manifest_path.name + ".lock").exists()


def test_deeply_nested_manifest_is_rejected_without_replacement(
    config_file: Path, source_file: Path
) -> None:
    config = load_config(config_file)
    document = "[" * 10_000 + "0" + "]" * 10_000
    config.manifest_path.parent.mkdir(parents=True)
    config.manifest_path.write_text(document, encoding="utf-8")
    with pytest.raises(FoundationError):
        register_source(config, "synthetic", source_file)
    assert config.manifest_path.read_text(encoding="utf-8") == document
    assert not config.manifest_path.with_name(config.manifest_path.name + ".lock").exists()


def test_atomic_replace_failure_preserves_previous_manifest_and_cleans_state(
    config_file: Path,
    source_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_config(config_file)
    register_source(config, "synthetic", source_file)
    previous_bytes = config.manifest_path.read_bytes()
    previous_files = set(config.manifest_path.parent.iterdir())
    source_file.write_bytes(b"new synthetic source version")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("synthetic filesystem failure")

    monkeypatch.setattr("data_analysis.manifest.os.replace", fail_replace)
    with pytest.raises(FoundationError):
        register_source(config, "synthetic", source_file)
    assert config.manifest_path.read_bytes() == previous_bytes
    assert set(config.manifest_path.parent.iterdir()) == previous_files
    assert source_file.read_bytes() == b"new synthetic source version"
