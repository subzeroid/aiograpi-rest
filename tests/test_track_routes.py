from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from aiograpi_rest.dependencies import get_clients
from aiograpi_rest.main import app


def _track_payload(track_id="track-1"):
    return {
        "id": track_id,
        "title": "Track",
        "subtitle": "Artist",
        "display_artist": "Artist",
        "audio_cluster_id": 1,
        "highlight_start_times_in_ms": [0],
        "is_explicit": False,
        "dash_manifest": "",
        "has_lyrics": False,
        "audio_asset_id": 10,
        "duration_in_ms": 30000,
        "allows_saving": True,
        "territory_validity_periods": {},
    }


class FakeTrackClient:
    def __init__(self):
        self.calls = []

    async def track_info_by_id(self, track_id, max_id=""):
        self.calls.append(("track_info_by_id", track_id, max_id))
        return {"track": _track_payload(track_id), "max_id": max_id}

    async def track_info_by_canonical_id(self, music_canonical_id):
        self.calls.append(("track_info_by_canonical_id", music_canonical_id))
        return _track_payload("canonical-track")

    async def track_stream_info_by_id(self, track_id, max_id=""):
        self.calls.append(("track_stream_info_by_id", track_id, max_id))
        return {"items": [{"media": {"pk": 1}}], "max_id": max_id}

    async def track_download_by_url(self, url, filename="", folder=""):
        self.calls.append(("track_download_by_url", url, filename, str(folder)))
        return Path(__file__).resolve()

    async def music_in_feed_audio_browser(self, browse_session_id=None):
        self.calls.append(("music_in_feed_audio_browser", browse_session_id))
        return {"items": [_track_payload()], "browse_session_id": browse_session_id}


class FakeStorage:
    def __init__(self):
        self.client = FakeTrackClient()

    async def get(self, sessionid):
        return self.client

    def close(self):
        pass


@pytest.fixture
def storage():
    fake = FakeStorage()
    app.dependency_overrides[get_clients] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_track_music_routes_call_aiograpi_methods(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        by_id = await ac.get("/track", params={"sessionid": "sid", "id": "track-1", "max_id": "cursor"})
        by_canonical = await ac.get("/track", params={"sessionid": "sid", "canonical_id": "canonical-1"})
        missing_selector = await ac.get("/track", params={"sessionid": "sid"})
        conflicting_selector = await ac.get(
            "/track",
            params={"sessionid": "sid", "id": "track-1", "canonical_id": "canonical-1"},
        )
        stream = await ac.get("/track/stream", params={"sessionid": "sid", "id": "track-1", "max_id": "stream"})
        download_path = await ac.get(
            "/track/download/by/url",
            params={"sessionid": "sid", "url": "https://example.com/audio.mp3", "returnFile": "false"},
        )
        download_file = await ac.get(
            "/track/download/by/url",
            params={"sessionid": "sid", "url": "https://example.com/audio.mp3", "filename": "track.mp3"},
        )
        browser = await ac.get(
            "/music/feed/browser",
            params={"sessionid": "sid", "browse_session_id": "browser-1"},
        )

    assert by_id.status_code == 200 and by_id.json()["track"]["id"] == "track-1"
    assert by_canonical.status_code == 200 and by_canonical.json()["id"] == "canonical-track"
    assert missing_selector.status_code == 422
    assert conflicting_selector.status_code == 422
    assert stream.status_code == 200 and stream.json()["max_id"] == "stream"
    assert download_path.status_code == 200 and download_path.json().endswith("test_track_routes.py")
    assert download_file.status_code == 200 and b"FakeTrackClient" in download_file.content
    assert browser.status_code == 200 and browser.json()["browse_session_id"] == "browser-1"
    assert ("track_info_by_id", "track-1", "cursor") in storage.client.calls
    assert ("track_info_by_canonical_id", "canonical-1") in storage.client.calls
    assert ("track_stream_info_by_id", "track-1", "stream") in storage.client.calls
    assert ("track_download_by_url", "https://example.com/audio.mp3", "", ".") in storage.client.calls
    assert ("track_download_by_url", "https://example.com/audio.mp3", "track.mp3", ".") in storage.client.calls
    assert ("music_in_feed_audio_browser", "browser-1") in storage.client.calls
