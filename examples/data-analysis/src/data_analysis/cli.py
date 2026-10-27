"""JSON command-line interface for configuration and source provenance."""

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from data_analysis.baseline import ECC_COMMIT, ECC_REPOSITORY, ECC_VERSION
from data_analysis.config import load_config
from data_analysis.errors import FoundationError
from data_analysis.manifest import load_manifest
from data_analysis.provenance import register_source


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fundação local de análise de dados e proveniência."
    )
    parser.add_argument("--config", type=Path, required=True, help="Arquivo TOML de configuração.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Consultar o estado sem gravar arquivos.")
    register = commands.add_parser("register-source", help="Registrar a identidade de um original.")
    register.add_argument("--source-id", required=True)
    register.add_argument("--file", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        config = load_config(arguments.config)
        if arguments.command == "status":
            manifest = load_manifest(config.manifest_path)
            output = {
                "project": config.name,
                "ecc": {"repository": ECC_REPOSITORY, "commit": ECC_COMMIT, "version": ECC_VERSION},
                "registered_sources": len(manifest.records),
                "analysis_ready": False,
                "state": "sources_registered" if manifest.records else "awaiting_datasets",
            }
        else:
            registration = register_source(config, arguments.source_id, arguments.file)
            output = {"created": registration.created, "source": asdict(registration.record)}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except FoundationError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 2
