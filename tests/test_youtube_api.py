import logging
from datetime import UTC, datetime

import httpx
import pytest

from lt.discovery.youtube.api import (
    YouTubeAPIError,
    YouTubeClient,
    parse_duration,
    parse_videos,
)
from tests.youtube_fakes import CHANNEL_ID, UPLOADS_ID, fake_youtube_transport, load


def _client(requests: list[httpx.Request] | None = None) -> YouTubeClient:
    return YouTubeClient(api_key="test-key", transport=fake_youtube_transport(requests))


@pytest.mark.parametrize(
    ("iso", "seconds"),
    [("PT53M40S", 3220), ("PT1H37M49S", 5869), ("PT3H43M", 13380), ("PT45S", 45), ("P0D", 0)],
)
def test_parse_duration(iso: str, seconds: int) -> None:
    assert parse_duration(iso) == seconds


def test_parse_duration_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="duration"):
        parse_duration("53 minutes")


def test_parse_videos_reads_livestream_details() -> None:
    videos = {v.video_id: v for v in parse_videos(load("videos.json"))}

    ws = videos["C4LHS4hEF-w"]
    assert ws.title == "Town Council Work Session 092826"
    assert ws.actual_start == datetime(2026, 9, 28, 23, 0, 3, tzinfo=UTC)
    assert ws.duration_s == 5869
    assert ws.channel_id == CHANNEL_ID


def test_uploads_playlist_id() -> None:
    assert _client().uploads_playlist_id(CHANNEL_ID) == UPLOADS_ID


def test_list_upload_ids_follows_pagination() -> None:
    requests: list[httpx.Request] = []

    ids = list(_client(requests).list_upload_ids(UPLOADS_ID))

    assert len(ids) == 50 + 38
    assert ids[0] == "M3rBK26yn0M"
    page_requests = [r for r in requests if r.url.path.endswith("/playlistItems")]
    assert len(page_requests) == 2
    assert page_requests[1].url.params.get("pageToken")


def test_get_videos_batches_ids_by_50() -> None:
    requests: list[httpx.Request] = []
    ids = [f"id{n}" for n in range(120)]

    list(_client(requests).get_videos(ids))

    batches = [r.url.params["id"].split(",") for r in requests if r.url.path.endswith("/videos")]
    assert [len(b) for b in batches] == [50, 50, 20]


def test_api_key_goes_in_a_header_never_the_url() -> None:
    """URLs end up in logs and proxies; the key must not."""
    requests: list[httpx.Request] = []

    _client(requests).uploads_playlist_id(CHANNEL_ID)

    assert requests[0].headers["x-goog-api-key"] == "test-key"
    assert "test-key" not in str(requests[0].url)
    assert "ClearViewBot" in requests[0].headers["user-agent"]


def test_key_never_appears_in_logs_at_debug_level(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)

    list(_client().list_upload_ids(UPLOADS_ID))

    assert caplog.records  # httpx did log the requests...
    assert "test-key" not in caplog.text  # ...without the key


def test_api_errors_raise_without_leaking_the_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "quotaExceeded"}})

    client = YouTubeClient(api_key="secret-key", transport=httpx.MockTransport(handler))

    with pytest.raises(YouTubeAPIError) as exc:
        client.uploads_playlist_id(CHANNEL_ID)
    assert "quotaExceeded" in str(exc.value)
    assert "secret-key" not in str(exc.value)
