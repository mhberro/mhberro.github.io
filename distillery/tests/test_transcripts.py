"""Tests for playlist and transcript utilities."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Self, cast

import pytest

from distillery.transcripts import (
    PlaylistVideo,
    _http_get_json,
    build_transcript_markdown,
    download_playlist_transcripts,
    fetch_playlist_metadata,
    fetch_playlist_videos,
    fetch_video_segments,
    format_timestamp,
    get_playlist_output_dir,
    slugify,
)


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class _TranscriptEntry:
    def __init__(self, text: str, start: float, duration: float) -> None:
        self.text = text
        self.start = start
        self.duration = duration


class _TranscriptApi:
    def __init__(self, entries: list[_TranscriptEntry]) -> None:
        self.entries = entries
        self.called_with: list[str] = []

    def fetch(self, video_id: str) -> list[_TranscriptEntry]:
        self.called_with.append(video_id)
        return self.entries


def test_slugify_and_timestamp_variants() -> None:
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("Málaga", allow_unicode=True) == "málaga"
    assert format_timestamp(65.2) == "01:05"
    assert format_timestamp(3661.9) == "01:01:01"


def test_http_get_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "distillery.transcripts.urlopen",
        lambda _url: _FakeResponse({"items": [{"id": 1}]}),
    )
    assert _http_get_json("https://example.com", {"q": "test"}) == {
        "items": [{"id": 1}]
    }


def test_fetch_playlist_videos_with_pagination() -> None:
    pages = [
        {
            "items": [
                {
                    "snippet": {
                        "title": "Video A",
                        "position": 1,
                        "playlistTitle": "Cloud Day",
                    },
                    "contentDetails": {"videoId": "vid-a"},
                },
                {"snippet": {"title": "Skip"}, "contentDetails": {}},
            ],
            "nextPageToken": "next",
        },
        {
            "items": [
                {
                    "snippet": {},
                    "contentDetails": {"videoId": "vid-b"},
                }
            ]
        },
    ]
    call_count = {"value": 0}

    def fake_http_get_json(
        _url: str, _params: Mapping[str, object]
    ) -> dict[str, object]:
        page = pages[call_count["value"]]
        call_count["value"] += 1
        return cast("dict[str, object]", page)

    videos = fetch_playlist_videos(
        "playlist", "token", http_get_json=fake_http_get_json
    )

    assert [v.video_id for v in videos] == ["vid-a", "vid-b"]
    assert videos[1].title == "vid-b"


def test_fetch_playlist_metadata_title_fallback() -> None:
    metadata = fetch_playlist_metadata(
        "playlist-id",
        "token",
        http_get_json=lambda _url, _params: {"items": []},
    )

    assert metadata.title == "playlist-id"
    assert metadata.videos == []


def test_fetch_playlist_metadata_skips_invalid_shapes() -> None:
    payload = {
        "items": [
            "not-a-dict",
            {"snippet": "bad", "contentDetails": "bad"},
        ]
    }
    metadata = fetch_playlist_metadata(
        "playlist-id",
        "token",
        http_get_json=lambda _url, _params: cast("dict[str, object]", payload),
    )

    assert metadata.videos == []


def test_fetch_playlist_metadata_handles_non_list_items() -> None:
    metadata = fetch_playlist_metadata(
        "playlist-id",
        "token",
        http_get_json=lambda _url, _params: cast(
            "dict[str, object]", {"items": "not-a-list"}
        ),
    )

    assert metadata.videos == []


def test_get_playlist_output_dir_slug_fallback(tmp_path: Path) -> None:
    no_title = get_playlist_output_dir(tmp_path, "!!!", "ABC-123")
    no_slug = get_playlist_output_dir(tmp_path, "!!!", "!!!")

    assert no_title == tmp_path / "abc-123"
    assert no_slug == tmp_path / "playlist"


def test_build_transcript_markdown() -> None:
    video = PlaylistVideo(video_id="abc", title="A title", position=0)
    content = build_transcript_markdown(video, [{"start": 12, "text": "line one"}])
    assert "# A title" in content
    assert "[00:12] line one" in content


def test_fetch_video_segments_with_and_without_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = [_TranscriptEntry("hello", 0.0, 3.5)]
    provided_api = _TranscriptApi(entries)

    segments = fetch_video_segments("video-1", transcript_api=provided_api)
    assert segments == [{"text": "hello", "start": 0.0, "duration": 3.5}]
    assert provided_api.called_with == ["video-1"]

    auto_api = _TranscriptApi(entries)
    monkeypatch.setattr("distillery.transcripts.YouTubeTranscriptApi", lambda: auto_api)
    auto_segments = fetch_video_segments("video-2")
    assert auto_segments == [{"text": "hello", "start": 0.0, "duration": 3.5}]
    assert auto_api.called_with == ["video-2"]


def test_download_playlist_transcripts_handles_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    videos = [
        PlaylistVideo(video_id="ok", title="Good Video", position=0),
        PlaylistVideo(video_id="bad", title="Bad Video", position=1),
    ]

    monkeypatch.setattr(
        "distillery.transcripts.fetch_playlist_videos", lambda **_kwargs: videos
    )

    def fake_fetch(video_id: str, **_kwargs: object) -> list[dict[str, object]]:
        if video_id == "bad":
            msg = "boom"
            raise RuntimeError(msg)
        return [{"start": 1, "text": "ok transcript", "duration": 2.0}]

    monkeypatch.setattr("distillery.transcripts.fetch_video_segments", fake_fetch)

    written = download_playlist_transcripts(
        "playlist",
        "api-key",
        tmp_path,
        playlist_name="KubeCon + CloudNativeCon",
    )

    assert len(written) == 1
    assert written[0].name == "000-good-video.md"
    assert written[0].parent.name == "kubecon-cloudnativecon"
    assert written[0].read_text(encoding="utf-8").startswith("# Good Video")


def test_download_playlist_transcripts_dry_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    videos = [PlaylistVideo(video_id="ok", title="Good Video", position=2)]

    monkeypatch.setattr(
        "distillery.transcripts.fetch_playlist_videos", lambda **_kwargs: videos
    )
    monkeypatch.setattr(
        "distillery.transcripts.fetch_video_segments",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not run")),
    )

    planned = download_playlist_transcripts(
        "playlist",
        "api-key",
        tmp_path,
        playlist_name="Playlist Name",
        dry_run=True,
    )

    assert planned == [tmp_path / "playlist-name" / "002-good-video.md"]
    assert not planned[0].exists()


def test_download_playlist_transcripts_without_playlist_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    videos = [PlaylistVideo(video_id="ok", title="Good Video", position=2)]

    monkeypatch.setattr(
        "distillery.transcripts.fetch_playlist_videos", lambda **_kwargs: videos
    )
    monkeypatch.setattr(
        "distillery.transcripts.fetch_video_segments",
        lambda *_args, **_kwargs: [{"start": 1, "text": "ok", "duration": 2.0}],
    )

    written = download_playlist_transcripts(
        "playlist",
        "api-key",
        tmp_path,
    )

    assert written == [tmp_path / "002-good-video.md"]
