# Copyright 2026 Lockheed Martin Corporation
# Lockheed Martin Proprietary Information

"""Top-level package for Distillery."""

import importlib.metadata


def _load_version() -> str:
    """Return the installed package version or a local fallback."""
    try:
        return importlib.metadata.version(__name__)
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"


__version__ = _load_version()
