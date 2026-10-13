"""Serve saved YouTube Data API responses through httpx.MockTransport."""

import json
from pathlib import Path

import httpx

API_DIR = Path(__file__).parent / "fixtures" / "youtube" / "api"
CHANNEL_ID = "UCtqtz4Sjo9chgA38RttUbdw"
UPLOADS_ID = "UUtqtz4Sjo9chgA38RttUbdw"


def load(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((API_DIR / name).read_text())
    return data


def fake_youtube_transport(requests: list[httpx.Request] | None = None) -> httpx.MockTransport:
    """Page 1 of uploads links to the saved last page; videos.list serves the saved batch."""
    videos = load("videos.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        params = request.url.params
        if request.url.path.endswith("/channels"):
            return httpx.Response(200, json=load("channels.json"))
        if request.url.path.endswith("/playlistItems"):
            name = (
                "playlist_items_last.json"
                if params.get("pageToken")
                else "playlist_items_page1.json"
            )
            return httpx.Response(200, json=load(name))
        if request.url.path.endswith("/videos"):
            wanted = set(params["id"].split(","))
            items = [v for v in videos["items"] if v["id"] in wanted]  # type: ignore[attr-defined]
            return httpx.Response(200, json={**videos, "items": items})
        return httpx.Response(404, json={"error": {"message": "not found"}})

    return httpx.MockTransport(handler)
