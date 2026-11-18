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

    async def music_search_v2(
        self,
        query,
        product="music_in_feed",
        from_typeahead=False,
        search_session_id=None,
        browse_session_id=None,
    ):
        self.calls.append(("music_search_v2", query, product, from_typeahead, search_session_id, browse_session_id))
        return {"items": [_track_payload("search-track")], "query": query}

    async def music_keyword_search(
        self,
        query,
        product="music_in_feed",
        num_keywords=3,
        search_session_id="",
        browse_session_id=None,
    ):
        self.calls.append(("music_keyword_search", query, product, num_keywords, search_session_id, browse_session_id))
        return {"keywords": [query], "num_keywords": num_keywords}

    async def music_trending(self, product="feed_post"):
        self.calls.append(("music_trending", product))
        return {"items": [_track_payload("trending-track")], "product": product}

    async def music_top_trends(self, product="music_in_feed", page_size=15):
        self.calls.append(("music_top_trends", product, page_size))
        return {"items": [_track_payload("top-trend")], "page_size": page_size}

    async def music_clips_audio_browser(self, product="story_camera_clips_v2", browse_session_id=None):
        self.calls.append(("music_clips_audio_browser", product, browse_session_id))
        return {"items": [_track_payload("clip-track")], "browse_session_id": browse_session_id}

    async def music_bookmark(self, original_audio_id, surface_requested_from="audio_aggregation_page"):
        self.calls.append(("music_bookmark", original_audio_id, surface_requested_from))
        return True

    async def music_verify_original_audio_title(self, original_audio_name):
        self.calls.append(("music_verify_original_audio_title", original_audio_name))
        return True


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
        music_search = await ac.get(
            "/music/search",
            params={
                "sessionid": "sid",
                "query": "rock",
                "product": "clips",
                "from_typeahead": "true",
                "search_session_id": "search-1",
                "browse_session_id": "browser-2",
            },
        )
        keywords = await ac.get(
            "/music/keywords",
            params={
                "sessionid": "sid",
                "query": "ro",
                "product": "clips",
                "num_keywords": "2",
                "search_session_id": "search-2",
                "browse_session_id": "browser-3",
            },
        )
        trending = await ac.get("/music/trending", params={"sessionid": "sid", "product": "story"})
        top_trends = await ac.get(
            "/music/trends/top",
            params={"sessionid": "sid", "product": "feed", "page_size": "5"},
        )
        clips_browser = await ac.get(
            "/music/clips/browser",
            params={"sessionid": "sid", "product": "clips", "browse_session_id": "browser-4"},
        )
        bookmark = await ac.post(
            "/music/bookmark",
            data={"sessionid": "sid", "original_audio_id": "audio-1", "surface_requested_from": "clips"},
        )
        original_audio_title = await ac.get(
            "/music/original-audio/title/availability",
            params={"sessionid": "sid", "name": "Original title"},
        )

    assert by_id.status_code == 200 and by_id.json()["track"]["id"] == "track-1"
    assert by_canonical.status_code == 200 and by_canonical.json()["id"] == "canonical-track"
    assert missing_selector.status_code == 422
    assert conflicting_selector.status_code == 422
    assert stream.status_code == 200 and stream.json()["max_id"] == "stream"
    assert download_path.status_code == 200 and download_path.json().endswith("test_track_routes.py")
    assert download_file.status_code == 200 and b"FakeTrackClient" in download_file.content
    assert browser.status_code == 200 and browser.json()["browse_session_id"] == "browser-1"
    assert music_search.status_code == 200 and music_search.json()["query"] == "rock"
    assert keywords.status_code == 200 and keywords.json()["num_keywords"] == 2
    assert trending.status_code == 200 and trending.json()["product"] == "story"
    assert top_trends.status_code == 200 and top_trends.json()["page_size"] == 5
    assert clips_browser.status_code == 200 and clips_browser.json()["browse_session_id"] == "browser-4"
    assert bookmark.status_code == 200 and bookmark.json() is True
    assert original_audio_title.status_code == 200 and original_audio_title.json() is True
    assert ("track_info_by_id", "track-1", "cursor") in storage.client.calls
    assert ("track_info_by_canonical_id", "canonical-1") in storage.client.calls
    assert ("track_stream_info_by_id", "track-1", "stream") in storage.client.calls
    assert ("track_download_by_url", "https://example.com/audio.mp3", "", "") in storage.client.calls
    assert ("track_download_by_url", "https://example.com/audio.mp3", "track.mp3", "") in storage.client.calls
    assert ("music_in_feed_audio_browser", "browser-1") in storage.client.calls
    assert ("music_search_v2", "rock", "clips", True, "search-1", "browser-2") in storage.client.calls
    assert ("music_keyword_search", "ro", "clips", 2, "search-2", "browser-3") in storage.client.calls
    assert ("music_trending", "story") in storage.client.calls
    assert ("music_top_trends", "feed", 5) in storage.client.calls
    assert ("music_clips_audio_browser", "clips", "browser-4") in storage.client.calls
    assert ("music_bookmark", "audio-1", "clips") in storage.client.calls
    assert ("music_verify_original_audio_title", "Original title") in storage.client.calls
