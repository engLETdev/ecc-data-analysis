"""Strict TOML configuration with paths anchored to its own location."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from data_analysis.baseline import SCHEMA_VERSION
from data_analysis.errors import FoundationError
from data_analysis.validation import exact_fields, nonempty_text


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    raw_dir: Path
    manifest_path: Path


def _storage_path(value: object, directory: Path) -> Path:
    text = nonempty_text(value)
    path = Path(text).expanduser()
    return (path if path.is_absolute() else directory / path).resolve()


def load_config(path: Path) -> ProjectConfig:
    """Read configuration without creating directories or modifying files."""
    try:
        resolved = Path(path).resolve(strict=True)
        with resolved.open("rb") as handle:
            data = tomllib.load(handle)
        root = exact_fields(data, {"schema_version", "project", "storage"})
        if type(root["schema_version"]) is not int or root["schema_version"] != SCHEMA_VERSION:
            raise FoundationError("Versão de esquema da configuração não suportada.")
        project = exact_fields(root["project"], {"name"})
        storage = exact_fields(root["storage"], {"raw_dir", "manifest"})
        raw_dir = _storage_path(storage["raw_dir"], resolved.parent)
        manifest = _storage_path(storage["manifest"], resolved.parent)
        if manifest.is_relative_to(raw_dir):
            raise FoundationError("O manifesto deve ficar fora do diretório de originais.")
        if raw_dir.exists() and not raw_dir.is_dir():
            raise FoundationError("O diretório de originais não pode ser um arquivo.")
        if manifest.is_dir():
            raise FoundationError("O destino do manifesto deve ser um arquivo.")
        return ProjectConfig(nonempty_text(project["name"]), raw_dir, manifest)
    except (OSError, ValueError, RuntimeError) as error:
        raise FoundationError("Não foi possível ler uma configuração TOML válida.") from error
