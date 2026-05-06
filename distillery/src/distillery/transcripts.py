"""Playlist transcript retrieval and markdown export."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import urlencode
from urllib.request import urlopen

from youtube_transcript_api import (
    VideoUnavailable,
    VideoUnplayable,
    YouTubeTranscriptApi,
)

if TYPE_CHECKING:
    from pathlib import Path

JsonValue = object
JsonDict = dict[str, JsonValue]
HttpGetJson = Callable[[str, Mapping[str, JsonValue]], JsonDict]


class TranscriptEntry(Protocol):
    """Transcript entry contract used during markdown generation."""

    text: str
    start: float
    duration: float


class TranscriptApiClient(Protocol):
    """Protocol for transcript API clients used by this module."""

    def fetch(self, video_id: str) -> Iterable[TranscriptEntry]:
        """Fetch transcript entries for a YouTube video."""
        ...


logger = logging.getLogger(__name__)

YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"


@dataclass(frozen=True, slots=True)
class PlaylistVideo:
    """Normalized playlist video metadata used by the exporter."""

    video_id: str
    title: str
    position: int


@dataclass(frozen=True, slots=True)
class PlaylistMetadata:
    """Playlist details and normalized video metadata."""

    title: str
    videos: list[PlaylistVideo]


def slugify(value: str, *, allow_unicode: bool = False) -> str:
    """Convert arbitrary text into a filesystem-safe slug."""
    normalized = str(value)
    if allow_unicode:
        normalized = unicodedata.normalize("NFKC", normalized)
    else:
        normalized = (
            unicodedata.normalize("NFKD", normalized)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    cleaned = re.sub(r"[^\w\s-]", "", normalized.lower())
    return re.sub(r"[-\s]+", "-", cleaned).strip("-_")


def format_timestamp(seconds: float) -> str:
    """Render seconds as HH:MM:SS or MM:SS."""
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _http_get_json(url: str, params: Mapping[str, JsonValue]) -> JsonDict:
    query = urlencode(params)
    with urlopen(f"{url}?{query}") as response:  # noqa: S310
        return cast("JsonDict", json.loads(response.read().decode("utf-8")))


def fetch_playlist_metadata(
    playlist_id: str,
    api_key: str,
    *,
    http_get_json: HttpGetJson = _http_get_json,
) -> PlaylistMetadata:
    """Fetch playlist title and all videos from a YouTube playlist."""
    items: list[PlaylistVideo] = []
    next_page_token: str | None = ""
    playlist_title: str | None = None

    while next_page_token is not None:
        payload = http_get_json(
            YOUTUBE_PLAYLIST_ITEMS_URL,
            {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
                "key": api_key,
                "pageToken": next_page_token,
            },
        )
        raw_items = payload.get("items", [])
        if not isinstance(raw_items, list):
            raw_items = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue
            snippet = item.get("snippet", {})
            if not isinstance(snippet, dict):
                snippet = {}
            content_details = item.get("contentDetails", {})
            if not isinstance(content_details, dict):
                content_details = {}

            raw_playlist_title = snippet.get("playlistTitle")
            if playlist_title is None and isinstance(raw_playlist_title, str):
                playlist_title = raw_playlist_title

            raw_video_id = content_details.get("videoId")
            video_id = raw_video_id if isinstance(raw_video_id, str) else None
            if video_id is None:
                continue

            raw_title = snippet.get("title")
            raw_position = snippet.get("position", len(items))
            items.append(
                PlaylistVideo(
                    video_id=video_id,
                    title=raw_title if isinstance(raw_title, str) else video_id,
                    position=int(raw_position),
                )
            )
        raw_next_page_token = payload.get("nextPageToken")
        next_page_token = (
            raw_next_page_token if isinstance(raw_next_page_token, str) else None
        )

    return PlaylistMetadata(
        title=playlist_title or playlist_id,
        videos=sorted(items, key=lambda video: video.position),
    )


def fetch_playlist_videos(
    playlist_id: str,
    api_key: str,
    *,
    http_get_json: HttpGetJson = _http_get_json,
) -> list[PlaylistVideo]:
    """Fetch all videos from a YouTube playlist."""
    return fetch_playlist_metadata(
        playlist_id=playlist_id,
        api_key=api_key,
        http_get_json=http_get_json,
    ).videos


def get_playlist_output_dir(
    output_dir: Path, playlist_title: str, playlist_id: str
) -> Path:
    """Create a stable playlist subdirectory path under output."""
    slug = slugify(playlist_title) or slugify(playlist_id) or "playlist"
    return output_dir / slug


def build_transcript_markdown(video: PlaylistVideo, segments: list[JsonDict]) -> str:
    """Build the markdown content for one transcript file."""
    lines = [
        f"# {video.title}",
        "",
        f"Video: https://www.youtube.com/watch?v={video.video_id}",
        "",
        "## Transcript",
        "",
    ]

    for segment in segments:
        raw_start = segment.get("start", 0)
        start = raw_start if isinstance(raw_start, (int, float)) else 0
        stamp = format_timestamp(float(start))
        text = str(segment.get("text", "")).strip()
        lines.append(f"- [{stamp}] {text}")

    lines.append("")
    return "\n".join(lines)


def fetch_video_segments(
    video_id: str,
    *,
    transcript_api: TranscriptApiClient | None = None,
) -> list[JsonDict]:
    """Fetch transcript snippets for a single video."""
    api = transcript_api or cast("TranscriptApiClient", YouTubeTranscriptApi())
    fetched_transcript = api.fetch(video_id)
    return [
        {
            "text": entry.text,
            "start": float(entry.start),
            "duration": float(entry.duration),
        }
        for entry in fetched_transcript
    ]


def download_playlist_transcripts(  # noqa: PLR0913
    playlist_id: str,
    api_key: str,
    output_dir: Path,
    *,
    dry_run: bool = False,
    transcript_api: TranscriptApiClient | None = None,
    http_get_json: HttpGetJson = _http_get_json,
) -> list[Path]:
    """Download playlist transcripts and return written file paths."""
    videos = fetch_playlist_videos(
        playlist_id=playlist_id,
        api_key=api_key,
        http_get_json=http_get_json,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    written_files: list[Path] = []

    for video in videos:
        filename = f"{video.position:03d}-{slugify(video.title)}.md"
        target = output_dir / filename
        if dry_run:
            written_files.append(target)
            logger.info("Dry run: would write transcript for %s", video.title)
            continue

        try:
            segments = fetch_video_segments(
                video.video_id, transcript_api=transcript_api
            )
        except (VideoUnplayable, VideoUnavailable):
            continue

        except Exception:
            logger.exception("Failed to fetch transcript for video %s", video.video_id)
            continue

        target.write_text(build_transcript_markdown(video, segments), encoding="utf-8")
        written_files.append(target)
        logger.info("Wrote transcript for %s", video.title)

    return written_files
