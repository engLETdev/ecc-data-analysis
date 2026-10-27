"""Errors safe to present at the command-line boundary."""


class FoundationError(Exception):
    """Invalid configuration, source identity or local manifest operation."""
