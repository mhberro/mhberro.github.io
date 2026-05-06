"""Tests for logging configuration loader."""

import json
from pathlib import Path

import pytest

from distillery.logger import DEFAULT_LOGGING_CONFIG, _get_logger_config, setup_logger


def test_get_logger_config_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISTILLERY_LOGGING_CONFIG", raising=False)
    assert _get_logger_config() == DEFAULT_LOGGING_CONFIG


def test_get_logger_config_missing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "missing.json"
    monkeypatch.setenv("DISTILLERY_LOGGING_CONFIG", str(missing))

    with pytest.raises(FileNotFoundError):
        _get_logger_config()


def test_get_logger_config_invalid_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("not-json", encoding="utf-8")
    monkeypatch.setenv("DISTILLERY_LOGGING_CONFIG", str(broken))

    with pytest.raises(ValueError, match="Invalid JSON"):
        _get_logger_config()


def test_get_logger_config_custom_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    custom = tmp_path / "logging.json"
    payload = {"version": 1, "handlers": {}, "root": {"handlers": [], "level": "INFO"}}
    custom.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("DISTILLERY_LOGGING_CONFIG", str(custom))

    assert _get_logger_config() == payload


def test_setup_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_get_logger_config() -> dict[str, int]:
        return {"version": 1}

    def fake_dict_config(config: dict[str, object]) -> None:
        calls.append(config)

    monkeypatch.setattr("distillery.logger._get_logger_config", fake_get_logger_config)
    monkeypatch.setattr("logging.config.dictConfig", fake_dict_config)

    setup_logger()

    assert calls == [{"version": 1}]
