"""Minimal YouTube Data API v3 client.

We use the official API rather than scraping because YouTube's robots.txt disallows the
channel RSS feed and its terms restrict automated access to the site. Quota cost is low:
``playlistItems.list`` and ``videos.list`` are 1 unit per call of up to 50 items.
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from lt import __version__

API_BASE = "https://www.googleapis.com/youtube/v3"
USER_AGENT = f"ClearViewBot/{__version__} (+https://github.com/mmorrisj/ClearView)"
_BATCH = 50
_DURATION_RE = re.compile(
    r"^P(?:(?P<d>\d+)D)?(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?)?$"
)


class YouTubeAPIError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VideoInfo:
    video_id: str
    channel_id: str
    title: str
    published_at: datetime
    duration_s: int
    # Set only for livestreams that actually went live.
    actual_start: datetime | None = None
    actual_end: datetime | None = None

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


def parse_duration(iso: str) -> int:
    """ISO-8601 duration as used by YouTube (``PT1H2M3S``, ``P0D``) to whole seconds."""
    m = _DURATION_RE.match(iso)
    if not m or iso in ("P", "PT"):
        raise ValueError(f"unrecognized ISO-8601 duration: {iso!r}")
    d, h, mi, s = (int(m[g] or 0) for g in ("d", "h", "m", "s"))
    return ((d * 24 + h) * 60 + mi) * 60 + s


def _ts(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def parse_videos(payload: dict[str, Any]) -> list[VideoInfo]:
    """Parse a ``videos.list`` response (parts: snippet, contentDetails, liveStreamingDetails)."""
    videos = []
    for item in payload.get("items", []):
        snippet, live = item["snippet"], item.get("liveStreamingDetails", {})
        videos.append(
            VideoInfo(
                video_id=item["id"],
                channel_id=snippet["channelId"],
                title=snippet["title"],
                published_at=datetime.fromisoformat(snippet["publishedAt"]),
                duration_s=parse_duration(item["contentDetails"]["duration"]),
                actual_start=_ts(live.get("actualStartTime")),
                actual_end=_ts(live.get("actualEndTime")),
            )
        )
    return videos


class YouTubeClient:
    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        # The key goes in a header, never the query string: URLs are written to logs
        # (httpx logs every request at INFO) and to proxy access logs.
        self._http = httpx.Client(
            base_url=API_BASE,
            headers={"User-Agent": USER_AGENT, "X-goog-api-key": api_key},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def _get(self, path: str, **params: str | int) -> dict[str, Any]:
        response = self._http.get(path, params=params)
        if response.status_code != httpx.codes.OK:
            # Report only Google's error message, not the raw response.
            try:
                message = response.json()["error"]["message"]
            except (ValueError, KeyError, TypeError):
                message = response.text[:200]
            raise YouTubeAPIError(f"{path} returned {response.status_code}: {message}")
        data: dict[str, Any] = response.json()
        return data

    def uploads_playlist_id(self, channel_id: str) -> str:
        data = self._get("/channels", id=channel_id, part="contentDetails")
        if not data.get("items"):
            raise YouTubeAPIError(f"channel not found: {channel_id}")
        playlist: str = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        return playlist

    def list_upload_ids(self, playlist_id: str) -> Iterator[str]:
        """Yield video ids in the uploads playlist, newest first, following pagination."""
        page_token: str | None = None
        while True:
            params: dict[str, str | int] = {
                "playlistId": playlist_id,
                "part": "contentDetails",
                "maxResults": _BATCH,
            }
            if page_token:
                params["pageToken"] = page_token
            data = self._get("/playlistItems", **params)
            for item in data.get("items", []):
                yield item["contentDetails"]["videoId"]
            page_token = data.get("nextPageToken")
            if not page_token:
                return

    def get_videos(self, video_ids: Iterable[str]) -> Iterator[VideoInfo]:
        ids = list(video_ids)
        for start in range(0, len(ids), _BATCH):
            batch = ids[start : start + _BATCH]
            data = self._get(
                "/videos", id=",".join(batch), part="snippet,contentDetails,liveStreamingDetails"
            )
            yield from parse_videos(data)
