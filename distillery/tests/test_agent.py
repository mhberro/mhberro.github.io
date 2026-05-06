"""Tests for Distillery transcript agent."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Protocol, cast

import pytest

from distillery.agent import DistilledTranscript, DistilleryAgent

if TYPE_CHECKING:
    from pathlib import Path


class _ProviderLike(Protocol):
    api_key: str | None


def test_distillery_agent_init_uses_env_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "clip.md"
    transcript.write_text("content", encoding="utf-8")
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, *, base_url: str, api_key: str | None) -> None:
            self.base_url = base_url
            self.api_key = api_key

    class FakeModel:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setenv("OPENAI_API_KEY", "env-secret")
    monkeypatch.setattr("distillery.agent.OpenAIProvider", FakeProvider)
    monkeypatch.setattr("distillery.agent.OpenAIChatModel", FakeModel)

    DistilleryAgent(transcript=transcript, api_base_url="https://example.test/v1")

    provider = cast("_ProviderLike", captured["provider"])
    assert provider.api_key == "env-secret"


@pytest.mark.asyncio
async def test_distil_creates_summary_wisdom_and_insights(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "clip.md"
    transcript.write_text("transcript body", encoding="utf-8")

    patterns_dir = tmp_path / "patterns"
    (patterns_dir / "youtube_summary").mkdir(parents=True)
    (patterns_dir / "extract_wisdom").mkdir(parents=True)
    (patterns_dir / "extract_insights").mkdir(parents=True)
    (patterns_dir / "youtube_summary" / "system.md").write_text(
        "summary instructions", encoding="utf-8"
    )
    (patterns_dir / "extract_wisdom" / "system.md").write_text(
        "wisdom instructions", encoding="utf-8"
    )
    (patterns_dir / "extract_insights" / "system.md").write_text(
        "insights instructions", encoding="utf-8"
    )

    class FakeModel:
        def __init__(self, **_kwargs: object) -> None:
            return None

    class FakeRuntimeAgent:
        def __init__(self, _model: object, instructions: str) -> None:
            self.instructions = instructions

        async def run(self, content: str) -> object:
            if "summary" in self.instructions:
                return SimpleNamespace(output=f"SUMMARY::{content}")
            if "wisdom" in self.instructions:
                return SimpleNamespace(output=f"WISDOM::{content}")
            return SimpleNamespace(output=f"INSIGHTS::{content}")

    monkeypatch.setattr("distillery.agent.OpenAIChatModel", FakeModel)
    monkeypatch.setattr("distillery.agent.Agent", FakeRuntimeAgent)

    distil_agent = DistilleryAgent(transcript=transcript, api_key="secret")
    distil_agent.patterns_dir = patterns_dir

    output = await distil_agent.distil()

    assert isinstance(output, DistilledTranscript)
    assert output.summary == "SUMMARY::transcript body"
    assert output.wisdom == "WISDOM::SUMMARY::transcript body"
    assert output.insights == "INSIGHTS::SUMMARY::transcript body"

    assert (tmp_path / "clip_summary.md").read_text(encoding="utf-8") == output.summary
    assert (tmp_path / "clip_wisdom.md").read_text(encoding="utf-8") == output.wisdom
    assert (tmp_path / "clip_insights.md").read_text(
        encoding="utf-8"
    ) == output.insights


def test_write_helpers_write_expected_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "clip.md"
    transcript.write_text("transcript body", encoding="utf-8")

    class FakeModel:
        def __init__(self, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr("distillery.agent.OpenAIChatModel", FakeModel)

    distil_agent = DistilleryAgent(transcript=transcript, api_key="secret")

    distil_agent.write_summary("summary")
    distil_agent.write_wisdom("wisdom")
    distil_agent.write_insights("insights")

    assert (tmp_path / "clip_summary.md").read_text(encoding="utf-8") == "summary"
    assert (tmp_path / "clip_wisdom.md").read_text(encoding="utf-8") == "wisdom"
    assert (tmp_path / "clip_insights.md").read_text(encoding="utf-8") == "insights"
