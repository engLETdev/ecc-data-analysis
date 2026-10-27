"""Validated immutable manifests and atomic writes under an exclusive lock."""

import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from data_analysis.baseline import ECC_COMMIT, SCHEMA_VERSION
from data_analysis.errors import FoundationError
from data_analysis.validation import (
    SHA256,
    exact_fields,
    nonempty_text,
    relative_source_path,
    validate_source_id,
)


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    relative_path: str
    sha256: str
    size_bytes: int
    registered_at: str


@dataclass(frozen=True)
class Manifest:
    records: tuple[SourceRecord, ...] = ()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len({key for key, _ in pairs}) != len(pairs):
        raise FoundationError("O manifesto contém campos repetidos.")
    return dict(pairs)


def _timestamp(value: Any) -> str:
    text = nonempty_text(value)
    try:
        instant = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise FoundationError("Data de registro inválida no manifesto.") from error
    if instant.tzinfo is None:
        raise FoundationError("A data de registro deve conter fuso horário.")
    return text


def _record(value: Any) -> SourceRecord:
    fields = exact_fields(
        value, {"source_id", "relative_path", "sha256", "size_bytes", "registered_at"}
    )
    digest = fields["sha256"]
    size = fields["size_bytes"]
    if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
        raise FoundationError("SHA-256 inválido no manifesto.")
    if type(size) is not int or size < 0:
        raise FoundationError("Tamanho de fonte inválido no manifesto.")
    return SourceRecord(
        validate_source_id(fields["source_id"]),
        relative_source_path(fields["relative_path"]),
        digest,
        size,
        _timestamp(fields["registered_at"]),
    )


def load_manifest(path: Path) -> Manifest:
    """Read a missing manifest as empty; never repair invalid state silently."""
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle, object_pairs_hook=_unique_object)
    except FileNotFoundError:
        return Manifest()
    except (OSError, ValueError, RecursionError) as error:
        raise FoundationError("Não foi possível ler um manifesto JSON válido.") from error
    root = exact_fields(data, {"schema_version", "ecc_commit", "sources"})
    if type(root["schema_version"]) is not int or root["schema_version"] != SCHEMA_VERSION:
        raise FoundationError("Versão de esquema do manifesto não suportada.")
    if root["ecc_commit"] != ECC_COMMIT or not isinstance(root["sources"], list):
        raise FoundationError("Referência ECC ou lista de fontes inválida no manifesto.")
    records = tuple(_record(value) for value in root["sources"])
    identities = {(record.source_id, record.sha256) for record in records}
    if len(identities) != len(records):
        raise FoundationError("O manifesto contém identidades de fonte duplicadas.")
    return Manifest(records)


@contextmanager
def writer_lock(path: Path) -> Iterator[None]:
    """One writer per manifest. Existing locks belong to another operation."""
    lock = path.with_name(path.name + ".lock")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError as error:
        raise FoundationError("Manifesto indisponível ou outro escritor mantém o lock.") from error
    try:
        os.close(descriptor)
        yield
    finally:
        try:
            lock.unlink()
        except OSError as error:
            raise FoundationError("Não foi possível liberar o lock do manifesto.") from error


def write_manifest(path: Path, manifest: Manifest) -> None:
    """Publish a complete file atomically; the caller must hold writer_lock."""
    data = {
        "schema_version": SCHEMA_VERSION,
        "ecc_commit": ECC_COMMIT,
        "sources": [asdict(record) for record in manifest.records],
    }
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".sources-", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise FoundationError("Não foi possível gravar o manifesto atomicamente.") from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError as error:
                raise FoundationError("Não foi possível remover o arquivo temporário.") from error
