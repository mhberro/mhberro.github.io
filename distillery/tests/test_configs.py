"""Tests for settings behavior and config logging."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr
from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource, YamlConfigSettingsSource

from distillery.configs import Configs


class _DummySource(PydanticBaseSettingsSource):
    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        _ = field
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        return {}


def test_settings_customise_sources_order() -> None:
    init = _DummySource(Configs)
    env = _DummySource(Configs)
    dotenv = _DummySource(Configs)
    secrets = _DummySource(Configs)

    result = Configs.settings_customise_sources(
        Configs,
        init,
        env,
        dotenv,
        secrets,
    )

    assert result[0] is secrets
    assert result[1] is init
    assert result[2] is env
    assert result[3] is dotenv
    assert isinstance(result[4], YamlConfigSettingsSource)


def test_youtube_api_key_env_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("YOUTUBE_API_KEY", "env-token")

    cfg = Configs(playlist_id="playlist-123", output=tmp_path)  # type: ignore[call-arg]

    assert cfg.youtube_api_key.get_secret_value() == "env-token"


def test_summary_logs_all_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = Configs(
        playlist_id="playlist-123",
        youtube_api_key=SecretStr("token"),
        output=tmp_path,
    )
    messages: list[tuple[str, tuple[object, ...]]] = []

    def fake_info(msg: str, *args: object) -> None:
        messages.append((msg, args))

    monkeypatch.setattr("distillery.configs.logger.info", fake_info)

    cfg.summary()

    assert "Beginning Rosalina" in messages[0][0]
    assert len(messages) == len(vars(cfg)) + 1
