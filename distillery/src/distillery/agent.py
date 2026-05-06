# Copyright 2026 Lockheed Martin Corporation
# Lockheed Martin Proprietary Information

"""Agent client for Distillery."""

from __future__ import annotations

import asyncio
import logging
from os import environ
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

logger = logging.getLogger(__name__)


class DistilledTranscript(BaseModel):
    """A collection of increasingly terse summarize for a transcript."""

    summary: str
    wisdom: str
    insights: str


class DistilleryAgent:
    """Async client for running prompts against transcript markdown."""

    def __init__(
        self,
        *,
        model_name: str,
        api_base_url: str,
        api_key: str | None = None,
    ) -> None:
        if api_key is None:
            api_key = environ.get("OPENAI_API_KEY", "")

        self.patterns_dir = Path(__file__).absolute().parent / "patterns"
        self.model = OpenAIChatModel(
            model_name=model_name,
            provider=OpenAIProvider(
                base_url=api_base_url,
                api_key=api_key,
            ),
            settings=ModelSettings(
                timeout=100,
                extra_headers={
                    "X-AIFACTORY-CLIENT": "distillery",
                },
            ),
        )
        summarize_instructions = (
            self.patterns_dir / "youtube_summary/system.md"
        ).read_text()
        wisdom_instructions = (
            self.patterns_dir / "extract_wisdom/system.md"
        ).read_text()
        insights_instructions = (
            self.patterns_dir / "extract_insights/system.md"
        ).read_text()

        self.summarize_agent = Agent(self.model, instructions=summarize_instructions)
        self.wisdom_agent = Agent(self.model, instructions=wisdom_instructions)
        self.insight_agent = Agent(self.model, instructions=insights_instructions)

    async def distil_transcripts(self, transcript_file: Path) -> DistilledTranscript:
        """Read transcript markdown from disk, then run distil prompts against it."""
        distil_base = f"{transcript_file.parent}/{transcript_file.stem}"
        distil_suffix = transcript_file.suffix
        summary_file = Path(f"{distil_base}_summary{distil_suffix}")
        wisdom_file = Path(f"{distil_base}_wisdom{distil_suffix}")
        insights_file = Path(f"{distil_base}_insights{distil_suffix}")

        transcript = await asyncio.to_thread(
            transcript_file.read_text, encoding="utf-8"
        )

        if not summary_file.exists():
            summary = (await self.summarize_agent.run(transcript)).output
            Path(summary_file).write_text(summary, encoding="utf-8")
        else:
            logger.warning("Summary for %s already exists.", transcript_file.name)
            summary = summary_file.read_text()

        if not wisdom_file.exists():
            wisdom = (await self.wisdom_agent.run(summary)).output
            Path(wisdom_file).write_text(wisdom, encoding="utf-8")
        else:
            logger.warning("Wisdom for %s already exists.", transcript_file.name)
            wisdom: str = wisdom_file.read_text()

        if not insights_file.exists():
            insights = (await self.insight_agent.run(summary)).output
            Path(insights_file).write_text(insights, encoding="utf-8")
        else:
            logger.warning("Insights for %s already exists.", transcript_file.name)
            insights: str = insights_file.read_text()

        return DistilledTranscript(
            summary=summary,
            wisdom=wisdom,
            insights=insights,
        )

    async def distil_summaries(self, playlist_dir: Path) -> str:
        """Second round of summary distilling."""
        output_file = playlist_dir / f"{playlist_dir.name}_summaries.md"
        if output_file.exists():
            logger.warning("Distilled summary already exists, skipping.")
            return ""

        logger.info("Distilling summaries for %s...", playlist_dir.name)
        content = ""
        for file in playlist_dir.glob("*_summary.*"):
            content += f"---\nfile: {file}\n---\n\n" + file.read_text() + "\n\n"

        distilled_summaries = await self.summarize_agent.run(content)
        output_file.write_text(distilled_summaries.output)
        return distilled_summaries.output

    async def distil_wisdoms(self, playlist_dir: Path) -> str:
        """Second round of wisdom distilling."""
        output_file = playlist_dir / f"{playlist_dir.name}_wisdoms.md"
        if output_file.exists():
            logger.warning("Distilled widsoms already exists, skipping.")
            return ""

        logger.info("Distilling widsoms for %s...", playlist_dir.name)
        content = ""
        for file in playlist_dir.glob("*_wisdom.*"):
            content += f"---\nfile: {file}\n---\n\n" + file.read_text() + "\n\n"

        distilled_wisdoms = await self.wisdom_agent.run(content)
        output_file.write_text(distilled_wisdoms.output)
        return distilled_wisdoms.output

    async def distil_insights(self, playlist_dir: Path) -> str:
        """Second round of insights distilling."""
        output_file = playlist_dir / f"{playlist_dir.name}_insight.md"
        if output_file.exists():
            logger.warning("Distilled insights already exists, skipping.")
            return ""

        logger.info("Distilling insights for %s...", playlist_dir.name)
        content = ""
        for file in playlist_dir.glob("*_insights.*"):
            content += f"---\nfile: {file}\n---\n\n" + file.read_text() + "\n\n"

        distilled_insights = await self.insight_agent.run(content)
        output_file.write_text(distilled_insights.output)
        return distilled_insights.output
