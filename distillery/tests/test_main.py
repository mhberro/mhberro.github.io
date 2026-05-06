"""Tests for CLI entrypoint orchestration."""

from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from distillery.configs import Configs
from distillery.main import (
    _is_source_transcript_file,
    _iter_source_transcript_files,
    distil_playlist,
    main,
)


def test_main_with_explicit_configs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = Configs(
        playlist_id="playlist",
        playlist_name="Playlist Name",
        youtube_api_key=SecretStr("token"),
        output=tmp_path,
    )
    calls = {"summary": 0, "logged": 0, "run": 0}
    captured: dict[str, object] = {}

    def fake_setup_logger() -> None:
        return None

    def fake_summary(_self: Configs) -> None:
        calls["summary"] = 1

    def fake_download_playlist_transcripts(**kwargs: object) -> list[Path]:
        captured.update(kwargs)
        return [tmp_path / "one.md", tmp_path / "two.md"]

    def fake_logger_info(*_args: object) -> None:
        calls["logged"] = 1

    def fake_asyncio_run(coroutine: Coroutine[Any, Any, Any]) -> None:
        calls["run"] = 1
        coroutine.close()

    monkeypatch.setattr("distillery.main.setup_logger", fake_setup_logger)
    monkeypatch.setattr(
        Configs,
        "summary",
        fake_summary,
    )
    monkeypatch.setattr(
        "distillery.main.download_playlist_transcripts",
        fake_download_playlist_transcripts,
    )
    monkeypatch.setattr("distillery.main.logger.info", fake_logger_info)
    monkeypatch.setattr("distillery.main.asyncio.run", fake_asyncio_run)

    main(cfgs=cfg)

    assert calls == {"summary": 1, "logged": 1, "run": 1}
    assert captured["dry_run"] is False
    assert captured["playlist_name"] == "Playlist Name"


def test_main_without_configs_uses_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class DummyConfigs:
        def __init__(self) -> None:
            self.playlist_id = "playlist"
            self.playlist_name = None
            self.youtube_api_key = SecretStr("token")
            self.output = tmp_path
            self.dry_run = True

        def summary(self) -> None:
            return None

    def fake_configs() -> DummyConfigs:
        return DummyConfigs()

    def fake_setup_logger() -> None:
        return None

    def fake_download_playlist_transcripts(**kwargs: object) -> list[Path]:
        captured.update(kwargs)
        return []

    def fake_logger_info(*_args: object) -> None:
        return None

    def fake_asyncio_run(coroutine: Coroutine[Any, Any, Any]) -> None:
        coroutine.close()

    monkeypatch.setattr("distillery.main.Configs", fake_configs)
    monkeypatch.setattr("distillery.main.setup_logger", fake_setup_logger)
    monkeypatch.setattr(
        "distillery.main.download_playlist_transcripts",
        fake_download_playlist_transcripts,
    )
    monkeypatch.setattr("distillery.main.logger.info", fake_logger_info)
    monkeypatch.setattr("distillery.main.asyncio.run", fake_asyncio_run)

    main(cfgs=None)

    assert captured["dry_run"] is True
    assert captured["playlist_name"] is None


def test_main_dry_run_skips_distillation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = Configs(
        playlist_id="playlist",
        youtube_api_key=SecretStr("token"),
        output=tmp_path,
        dry_run=True,
    )
    calls = {"run": 0}

    monkeypatch.setattr("distillery.main.setup_logger", lambda: None)
    monkeypatch.setattr(Configs, "summary", lambda _self: None)
    monkeypatch.setattr(
        "distillery.main.download_playlist_transcripts", lambda **_kwargs: []
    )
    monkeypatch.setattr("distillery.main.logger.info", lambda *_args: None)
    monkeypatch.setattr(
        "distillery.main.asyncio.run", lambda _coroutine: calls.__setitem__("run", 1)
    )

    main(cfgs=cfg)

    assert calls["run"] == 0


@pytest.mark.asyncio
async def test_distil_playlist_no_files_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    warnings: list[str] = []

    def fake_warning(message: str, _path: Path) -> None:
        warnings.append(message)

    monkeypatch.setattr("distillery.main.logger.warning", fake_warning)

    await distil_playlist(tmp_path)

    assert warnings == ["No transcript markdown files found in %s"]


def test_iter_source_transcript_files_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    assert _iter_source_transcript_files(missing) == []


@pytest.mark.asyncio
async def test_distil_playlist_filters_generated_and_directories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "000-source.md"
    source.write_text("content", encoding="utf-8")
    (tmp_path / "000-source_summary.md").write_text("summary", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("skip", encoding="utf-8")
    (tmp_path / "nested").mkdir()

    called: list[Path] = []

    class FakeDistilleryAgent:
        def __init__(self, *, transcript: Path) -> None:
            self.transcript = transcript

        async def distil(self) -> object:
            called.append(self.transcript)
            return object()

    monkeypatch.setattr("distillery.main.agent.DistilleryAgent", FakeDistilleryAgent)

    await distil_playlist(tmp_path)

    assert called == [source]


def test_is_source_transcript_file(tmp_path: Path) -> None:
    source = tmp_path / "000-source.md"
    source.write_text("x", encoding="utf-8")
    summary = tmp_path / "000-source_summary.md"
    summary.write_text("x", encoding="utf-8")
    non_markdown = tmp_path / "000-source.txt"
    non_markdown.write_text("x", encoding="utf-8")
    folder = tmp_path / "folder"
    folder.mkdir()

    assert _is_source_transcript_file(source) is True
    assert _is_source_transcript_file(summary) is False
    assert _is_source_transcript_file(non_markdown) is False
    assert _is_source_transcript_file(folder) is False
