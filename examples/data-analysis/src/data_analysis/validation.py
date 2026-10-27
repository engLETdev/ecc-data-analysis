"""Small strict validators shared by configuration and manifest readers."""

import re
from pathlib import PurePosixPath
from typing import Any

from data_analysis.errors import FoundationError

SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z", re.ASCII)
SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


def exact_fields(value: Any, names: set[str]) -> dict[str, Any]:
    """Reject missing and unknown fields, rather than silently guessing."""
    if not isinstance(value, dict) or set(value) != names:
        raise FoundationError("Campos obrigatórios ausentes ou desconhecidos.")
    return value


def nonempty_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise FoundationError("Um campo de texto obrigatório é inválido.")
    return value


def validate_source_id(value: Any) -> str:
    if not isinstance(value, str) or SOURCE_ID.fullmatch(value) is None:
        raise FoundationError("Identificador de fonte inválido; use 1 a 64 caracteres ASCII.")
    return value


def relative_source_path(value: Any) -> str:
    """Use normalized portable paths in records; never serialize absolute names."""
    text = nonempty_text(value)
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or "\\" in text or ":" in text:
        raise FoundationError("O manifesto contém um caminho de fonte inválido.")
    if not path.parts or path.as_posix() != text:
        raise FoundationError("O caminho da fonte deve ser relativo e normalizado.")
    return text
