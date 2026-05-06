"""Tests for package metadata utilities."""

import importlib.metadata

import pytest

from distillery import __version__, _load_version


def test_load_version_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(importlib.metadata, "version", lambda _: "1.2.3")
    assert _load_version() == "1.2.3"


def test_load_version_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_missing(_: str) -> str:
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", raise_missing)
    assert _load_version() == "0.0.0"


def test_version_export_is_string() -> None:
    assert isinstance(__version__, str)
