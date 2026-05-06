# Copyright 2026 Lockheed Martin Corporation
# Lockheed Martin Proprietary Information
"""CLI entrypoint for Distillery."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Annotated

import cyclopts
from cyclopts import App

from distillery import __version__, agent
from distillery.configs import Configs
from distillery.logger import setup_logger
from distillery.transcripts import (
    download_playlist_transcripts,
    get_playlist_output_dir,
)

app = App(name=" Distillery ", version=f"Distillery  {__version__}")
logger = logging.getLogger(__name__)


def _is_source_transcript_file(path: Path) -> bool:
    """Return True when file is a source transcript markdown file."""
    if not path.is_file() or path.suffix != ".md":
        return False

    generated_suffixes = ("_summary.md", "_wisdom.md", "_insights.md")
    return not path.name.endswith(generated_suffixes)


def _iter_source_transcript_files(directory: Path) -> list[Path]:
    """Return source transcript files under the provided directory."""
    if not directory.exists():
        return []
    return [path for path in directory.iterdir() if _is_source_transcript_file(path)]


async def distil_playlist(
    playlist_output_dir: Path, distil_agent: agent.DistilleryAgent
) -> None:
    """Concurrently distil multiple transcripts."""
    transcript_files = _iter_source_transcript_files(playlist_output_dir)
    if not transcript_files:
        logger.warning("No transcript markdown files found in %s", playlist_output_dir)
        return

    for file in transcript_files:
        await distil_agent.distil_transcripts(file)

    summaries = await distil_agent.distil_summaries(playlist_output_dir)
    wisdoms = await distil_agent.distil_wisdoms(playlist_output_dir)
    insights = await distil_agent.distil_insights(playlist_output_dir)

    distilled_output = playlist_output_dir / f"{playlist_output_dir.name}_distilled.md"
    if distilled_output.exists():
        logger.warning(
            "Distilled playlist output already exists at %s, skipping.",
            distilled_output,
        )
        return
    content = f"Summary\n---\n\n{summaries}\n\nWisdom\n---\n\n{wisdoms}\n\nInsights\n---\n\n{insights}\n"  # noqa: E501
    sys.stdout.write(content)
    distilled_output.write_text(content)


@app.default
def main(
    *, cfgs: Annotated[Configs, cyclopts.Parameter(name="*")] | None = None
) -> None:
    """Entrypoint for Distillery."""
    if cfgs is None:
        cfgs = Configs()  # type: ignore[call-arg]
    setup_logger()
    cfgs.summary()

    distil_agent = agent.DistilleryAgent(
        model_name=cfgs.model,
        api_base_url=cfgs.api_base_url,
    )
    playlist_output_dir = cfgs.output
    if cfgs.playlist_name:
        playlist_output_dir = get_playlist_output_dir(
            output_dir=cfgs.output,
            playlist_title=cfgs.playlist_name,
            playlist_id=cfgs.playlist_id,
        )

    if not cfgs.output.exists():
        written = download_playlist_transcripts(
            playlist_id=cfgs.playlist_id,
            api_key=cfgs.youtube_api_key.get_secret_value(),
            output_dir=cfgs.output,
            dry_run=cfgs.dry_run,
        )
        logger.info("Created %d transcript files", len(written))
    else:
        logger.warning("Output dir already exists, skipping transcript download")

    if cfgs.dry_run:
        logger.info("Dry run enabled, skipping distillation.")
        return

    asyncio.run(distil_playlist(playlist_output_dir, distil_agent))
