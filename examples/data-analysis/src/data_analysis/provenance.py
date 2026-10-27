"""Hash unchanged source bytes and register logical identities idempotently."""

import hashlib
import os
import stat
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from data_analysis.config import ProjectConfig
from data_analysis.errors import FoundationError
from data_analysis.manifest import (
    Manifest,
    SourceRecord,
    load_manifest,
    write_manifest,
    writer_lock,
)
from data_analysis.validation import relative_source_path, validate_source_id

CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class Fingerprint:
    sha256: str
    size_bytes: int
    _source_identity: tuple[int, ...] = field(default=(), repr=False, compare=False)


@dataclass(frozen=True)
class Registration:
    record: SourceRecord
    created: bool


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _source_identity(path: Path) -> tuple[int, ...]:
    observed = path.lstat()
    if not stat.S_ISREG(observed.st_mode):
        raise FoundationError("A fonte deve ser um arquivo regular sem link simbólico.")
    return _identity(observed)


def fingerprint_file(path: Path) -> Fingerprint:
    """Observe one stable regular file; reject detectable changes during reading."""
    try:
        expected = _source_identity(Path(path))
        digest = hashlib.sha256()
        size = 0
        with Path(path).open("rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode) or expected != _identity(before):
                raise FoundationError("A fonte mudou antes do cálculo de identidade.")
            while chunk := handle.read(CHUNK_BYTES):
                digest.update(chunk)
                size += len(chunk)
            after = os.fstat(handle.fileno())
        if _identity(before) != _identity(after) or _identity(after) != _source_identity(
            Path(path)
        ):
            raise FoundationError("A fonte mudou durante o cálculo de identidade.")
        if size != after.st_size:
            raise FoundationError("O tamanho lido não corresponde ao arquivo observado.")
        return Fingerprint(digest.hexdigest(), size, _identity(after))
    except OSError as error:
        raise FoundationError("Não foi possível ler a fonte local.") from error


def _resolve_source(config: ProjectConfig, source_path: Path) -> tuple[Path, str]:
    try:
        path = Path(source_path).resolve(strict=True)
        # load_config already resolved raw_dir. Re-resolving it here could move
        # the allowed boundary if a directory were replaced by an external link.
        relative = path.relative_to(config.raw_dir)
    except (OSError, ValueError, RuntimeError) as error:
        raise FoundationError("A fonte deve existir dentro do diretório de originais.") from error
    return path, relative_source_path(relative.as_posix())


def _assert_source_snapshot(
    config: ProjectConfig,
    path: Path,
    relative: str,
    expected: tuple[int, ...],
    fingerprint: Fingerprint,
) -> None:
    current_path, current_relative = _resolve_source(config, path)
    try:
        current = _source_identity(current_path)
    except OSError as error:
        raise FoundationError("Não foi possível revalidar a fonte local.") from error
    if (
        current_path != path
        or current_relative != relative
        or current != expected
        or fingerprint._source_identity != expected
    ):
        raise FoundationError("A localização ou identidade da fonte mudou durante o registro.")


def register_source(config: ProjectConfig, source_id: str, source_path: Path) -> Registration:
    """Register metadata only, retaining the first entry for each (ID, hash)."""
    logical_id = validate_source_id(source_id)
    path, relative = _resolve_source(config, source_path)
    try:
        expected = _source_identity(path)
    except OSError as error:
        raise FoundationError("Não foi possível validar a fonte local.") from error
    fingerprint = fingerprint_file(path)
    with writer_lock(config.manifest_path):
        current = load_manifest(config.manifest_path)
        _assert_source_snapshot(config, path, relative, expected, fingerprint)
        existing = next(
            (
                r
                for r in current.records
                if (r.source_id, r.sha256) == (logical_id, fingerprint.sha256)
            ),
            None,
        )
        if existing is not None:
            if existing.size_bytes != fingerprint.size_bytes:
                raise FoundationError("O tamanho registrado não confere com a identidade da fonte.")
            return Registration(existing, False)
        record = SourceRecord(
            source_id=logical_id,
            relative_path=relative,
            sha256=fingerprint.sha256,
            size_bytes=fingerprint.size_bytes,
            registered_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )
        write_manifest(config.manifest_path, Manifest((*current.records, record)))
        return Registration(record, True)
