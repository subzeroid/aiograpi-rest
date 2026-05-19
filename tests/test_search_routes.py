import pytest
from httpx import ASGITransport, AsyncClient

from aiograpi_rest.dependencies import get_clients
from aiograpi_rest.main import app


def _user_short(pk=1):
    return {"pk": str(pk), "username": f"user{pk}", "full_name": f"User {pk}"}


def _hashtag_payload(name="python"):
    return {"id": f"tag-{name}", "name": name, "media_count": 123}


def _location_payload(pk=1):
    return {"pk": pk, "name": "Berlin", "lat": 52.52, "lng": 13.405}


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


class FakeSearchClient:
    def __init__(self):
        self.calls = []

    async def search_hashtags(self, query):
        self.calls.append(("search_hashtags", query))
        return [_hashtag_payload(query)]

    async def search_music(self, query):
        self.calls.append(("search_music", query))
        return [_track_payload()]

    async def fbsearch_places(self, query, lat=40.74, lng=-73.94):
        self.calls.append(("fbsearch_places", query, lat, lng))
        return [_location_payload()]

    async def fbsearch_topsearch_v2(
        self,
        query,
        next_max_id=None,
        reels_max_id=None,
        rank_token=None,
    ):
        self.calls.append(("fbsearch_topsearch_v2", query, next_max_id, reels_max_id, rank_token))
        return {"items": [{"type": "user", "user": _user_short()}], "next_max_id": "next-top"}

    async def fbsearch_reels_v2(self, query, reels_max_id=None, rank_token=None):
        self.calls.append(("fbsearch_reels_v2", query, reels_max_id, rank_token))
        return {"items": [{"media": {"pk": 1}}], "reels_max_id": "next-reels"}

    async def fbsearch_accounts_v2(self, query, page_token=None):
        self.calls.append(("fbsearch_accounts_v2", query, page_token))
        return {"items": [_user_short()], "page_token": "next-accounts"}

    async def search_followers_v1(self, user_id, query):
        self.calls.append(("search_followers_v1", user_id, query))
        return [_user_short(2)]

    async def search_following_v1(self, user_id, query):
        self.calls.append(("search_following_v1", user_id, query))
        return [_user_short(3)]

    async def fbsearch_recent(self):
        self.calls.append(("fbsearch_recent",))
        return [(123, _user_short(4))]

    async def fbsearch_keyword_typeahead(self, query, timezone_offset=0, count=30):
        self.calls.append(("fbsearch_keyword_typeahead", query, timezone_offset, count))
        return {"items": [{"keyword": query}], "status": "ok"}


class FakeStorage:
    def __init__(self):
        self.client = FakeSearchClient()

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
async def test_search_p0_routes_call_aiograpi_methods(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        hashtags = await ac.get("/search/hashtags", params={"sessionid": "sid", "query": "python"})
        music = await ac.get("/search/music", params={"sessionid": "sid", "query": "rock"})
        places = await ac.get(
            "/search/places",
            params={"sessionid": "sid", "query": "Berlin", "lat": "52.52", "lng": "13.405"},
        )
        top = await ac.get(
            "/search/top",
            params={
                "sessionid": "sid",
                "query": "python",
                "next_max_id": "top-cursor",
                "reels_max_id": "reels-cursor",
                "rank_token": "rank",
            },
        )
        reels = await ac.get(
            "/search/reels",
            params={"sessionid": "sid", "query": "python", "reels_max_id": "reels-cursor", "rank_token": "rank"},
        )
        accounts = await ac.get(
            "/search/accounts",
            params={"sessionid": "sid", "query": "insta", "page_token": "accounts-cursor"},
        )
        followers = await ac.get(
            "/search/followers",
            params={"sessionid": "sid", "user_id": "1", "query": "alex"},
        )
        following = await ac.get(
            "/search/following",
            params={"sessionid": "sid", "user_id": "1", "query": "sam"},
        )
        recent = await ac.get("/search/recent", params={"sessionid": "sid"})
        typeahead = await ac.get(
            "/search/typeahead",
            params={"sessionid": "sid", "query": "py", "timezone_offset": "10800", "count": "5"},
        )

    for response in (
        hashtags,
        music,
        places,
        top,
        reels,
        accounts,
        followers,
        following,
        recent,
        typeahead,
    ):
        assert response.status_code == 200

    assert hashtags.json()[0]["name"] == "python"
    assert music.json()[0]["title"] == "Track"
    assert places.json()[0]["name"] == "Berlin"
    assert top.json()["next_max_id"] == "next-top"
    assert reels.json()["reels_max_id"] == "next-reels"
    assert accounts.json()["page_token"] == "next-accounts"
    assert followers.json()[0]["pk"] == "2"
    assert following.json()[0]["pk"] == "3"
    assert recent.json() == [{"timestamp": 123, "item": _user_short(4)}]
    assert typeahead.json()["items"][0]["keyword"] == "py"

    assert ("search_hashtags", "python") in storage.client.calls
    assert ("search_music", "rock") in storage.client.calls
    assert ("fbsearch_places", "Berlin", 52.52, 13.405) in storage.client.calls
    assert ("fbsearch_topsearch_v2", "python", "top-cursor", "reels-cursor", "rank") in storage.client.calls
    assert ("fbsearch_reels_v2", "python", "reels-cursor", "rank") in storage.client.calls
    assert ("fbsearch_accounts_v2", "insta", "accounts-cursor") in storage.client.calls
    assert ("search_followers_v1", "1", "alex") in storage.client.calls
    assert ("search_following_v1", "1", "sam") in storage.client.calls
    assert ("fbsearch_recent",) in storage.client.calls
    assert ("fbsearch_keyword_typeahead", "py", 10800, 5) in storage.client.calls
