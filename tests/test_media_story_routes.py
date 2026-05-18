import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

import aiograpi_rest.routers.media as media_router
import aiograpi_rest.routers.story as story_router
from aiograpi_rest.dependencies import get_clients
from aiograpi_rest.main import app


def _user_short(pk=1):
    return {"pk": str(pk), "username": f"u{pk}", "full_name": "Full"}


def _media_payload(pk=1):
    return {
        "pk": pk,
        "id": f"{pk}_42",
        "code": "abc",
        "taken_at": "2026-01-01T00:00:00+00:00",
        "media_type": 1,
        "user": _user_short(42),
        "like_count": 0,
        "caption_text": "",
        "usertags": [],
        "sponsor_tags": [],
    }


def _story_payload(pk=1):
    return {
        "pk": pk,
        "id": f"{pk}_42",
        "code": "abc",
        "taken_at": "2026-01-01T00:00:00+00:00",
        "media_type": 1,
        "user": _user_short(42),
        "sponsor_tags": [],
        "mentions": [],
        "links": [],
        "hashtags": [],
        "locations": [],
        "stickers": [],
    }


class FakeMediaClient:
    def __init__(self):
        self.calls = []
        self.story_unliked = None

    async def media_info(self, pk, use_cache=True):
        self.calls.append(("media_info", pk, use_cache))
        return _media_payload(pk=pk)

    async def user_medias_paginated(self, user_id, amount, end_cursor=""):
        self.calls.append(("user_medias_paginated", user_id, amount, end_cursor))
        return [_media_payload(pk=3)], "next-cursor"

    async def usertag_medias(self, user_id, amount):
        self.calls.append(("usertag_medias", user_id, amount))
        return [_media_payload(pk=2)]

    async def media_delete(self, media_id):
        self.calls.append(("media_delete", media_id))
        return True

    async def media_edit(self, media_id, caption, title, usertags, location):
        self.calls.append(("media_edit", media_id, caption, title, usertags, location))
        return {"caption": caption, "title": title}

    async def media_user(self, media_pk):
        self.calls.append(("media_user", media_pk))
        return _user_short(media_pk)

    async def media_oembed(self, url):
        self.calls.append(("media_oembed", url))
        return {"version": "1.0", "url": url}

    async def media_like(self, media_id, revert=False):
        self.calls.append(("media_like", media_id, revert))
        return True

    async def media_unlike(self, media_id):
        self.calls.append(("media_unlike", media_id))
        return True

    async def media_seen(self, media_ids, skipped_media_ids=None):
        self.calls.append(("media_seen", tuple(media_ids), tuple(skipped_media_ids or [])))
        return True

    async def media_likers(self, media_id):
        self.calls.append(("media_likers", media_id))
        return [_user_short(1), _user_short(2)]

    async def media_archive(self, media_id, revert=False):
        self.calls.append(("media_archive", media_id, revert))
        return True

    async def media_unarchive(self, media_id):
        self.calls.append(("media_unarchive", media_id))
        return True

    # Story methods
    async def user_stories(self, user_id, amount=None):
        self.calls.append(("user_stories", user_id, amount))
        return [_story_payload(pk=1)]

    async def story_info(self, story_pk, use_cache=True):
        self.calls.append(("story_info", story_pk, use_cache))
        return _story_payload(pk=story_pk)

    async def story_delete(self, story_pk):
        self.calls.append(("story_delete", story_pk))
        return True

    async def story_seen(self, story_pks, skipped_story_pks=None):
        self.calls.append(("story_seen", tuple(story_pks), tuple(skipped_story_pks or [])))
        return True

    async def story_like(self, story_id, revert=False):
        self.calls.append(("story_like", story_id, revert))
        return True

    async def story_unlike(self, story_id):
        self.calls.append(("story_unlike", story_id))
        self.story_unliked = story_id
        return True

    async def story_download(self, story_pk, filename, folder):
        self.calls.append(("story_download", story_pk, filename, str(folder)))
        return Path(__file__).resolve()

    async def story_download_by_url(self, url, filename, folder):
        self.calls.append(("story_download_by_url", url, filename, str(folder)))
        return Path(__file__).resolve()


class FakeStorage:
    def __init__(self):
        self.client = FakeMediaClient()

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


# Pure helper routes (no auth, no storage)
@pytest.mark.asyncio
async def test_media_pk_from_code_uses_aiograpi_helper():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/media/pk/from/code", params={"code": "B1LbfVPlwIA"})
    assert response.status_code == 200
    assert response.json() == "2110901750722920960"


@pytest.mark.asyncio
async def test_media_pk_uses_aiograpi_helper():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/media/pk", params={"media_id": "2110901750722920960_8572539084"}
        )
    assert response.status_code == 200
    assert response.json() == "2110901750722920960"


@pytest.mark.asyncio
async def test_media_pk_from_url_uses_aiograpi_helper():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/media/pk/from/url",
            params={"url": "https://instagram.com/p/B1LbfVPlwIA/"},
        )
    assert response.status_code == 200
    assert response.json() == "2110901750722920960"


@pytest.mark.asyncio
async def test_media_id_route_uses_client_factory(monkeypatch):
    class IdOnlyClient:
        async def media_id(self, media_pk):
            return f"{media_pk}_42"

    monkeypatch.setattr(media_router, "Client", lambda: IdOnlyClient())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/media/id", params={"media_pk": "100"})
    assert response.status_code == 200
    assert response.json() == "100_42"


@pytest.mark.asyncio
async def test_story_pk_from_url_uses_aiograpi_helper():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/story/pk/from/url",
            params={
                "url": "https://instagram.com/stories/instagram/2110901750722920960/"
            },
        )
    assert response.status_code == 200
    assert response.json() == 2110901750722920960


# Authenticated media routes
@pytest.mark.asyncio
async def test_media_info_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/media/info", params={"sessionid": "sid", "pk": "1"}
        )
    assert response.status_code == 200
    assert response.json()["pk"] == 1


@pytest.mark.asyncio
async def test_user_medias_returns_items_and_cursor(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/media/user/medias",
            params={
                "sessionid": "sid",
                "user_id": "1",
                "amount": "10",
                "end_cursor": "cursor",
            },
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["pk"] == 3
    assert response.json()["end_cursor"] == "next-cursor"
    assert ("user_medias_paginated", "1", 10, "cursor") in storage.client.calls


@pytest.mark.asyncio
async def test_usertag_medias_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/media/usertag/medias",
            params={"sessionid": "sid", "user_id": "1"},
        )
    assert response.status_code == 200
    assert ("usertag_medias", 1, 50) in storage.client.calls


@pytest.mark.asyncio
async def test_media_delete_returns_true(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(
            "/media", params={"sessionid": "sid", "media_id": "m1"}
        )
    assert response.status_code == 200
    assert response.json() is True


@pytest.mark.asyncio
async def test_media_edit_returns_dict(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/media",
            data={
                "sessionid": "sid",
                "media_id": "m1",
                "caption": "hello",
                "title": "title",
            },
        )
    assert response.status_code == 200
    assert response.json() == {"caption": "hello", "title": "title"}


@pytest.mark.asyncio
async def test_media_edit_ignores_blank_optional_usertags_and_location(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/media",
            data={
                "sessionid": "sid",
                "media_id": "m1",
                "caption": "hello",
                "usertags": "",
                "location": "",
            },
        )
    assert response.status_code == 200
    call = next(call for call in storage.client.calls if call[0] == "media_edit")
    assert call[4] == []
    assert call[5] is None


@pytest.mark.asyncio
async def test_media_edit_accepts_json_array_usertags_and_json_location(storage):
    usertags = json.dumps(
        [
            {"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5},
            {"user": {"pk": 2, "username": "v", "full_name": "g"}, "x": 0.2, "y": 0.8},
        ]
    )
    location = json.dumps({"pk": 1, "name": "Place", "lat": 10.0, "lng": 20.0})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/media",
            data={
                "sessionid": "sid",
                "media_id": "m1",
                "caption": "hello",
                "usertags": usertags,
                "location": location,
            },
        )
    assert response.status_code == 200
    call = next(call for call in storage.client.calls if call[0] == "media_edit")
    assert [tag.user.pk for tag in call[4]] == ["1", "2"]
    assert call[5].name == "Place"


@pytest.mark.asyncio
async def test_media_edit_rejects_invalid_usertags_json(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/media",
            data={
                "sessionid": "sid",
                "media_id": "m1",
                "caption": "hello",
                "usertags": "{bad-json",
            },
        )
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid JSON object for form field 'usertags'"


@pytest.mark.asyncio
async def test_media_edit_rejects_invalid_location_json(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/media",
            data={
                "sessionid": "sid",
                "media_id": "m1",
                "caption": "hello",
                "location": "{bad-json",
            },
        )
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid JSON object for form field 'location'"


@pytest.mark.asyncio
async def test_media_user_returns_author(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/media/user", params={"sessionid": "sid", "media_pk": "7"}
        )
    assert response.status_code == 200
    assert response.json()["pk"] == "7"


@pytest.mark.asyncio
async def test_media_oembed_returns_dict(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/media/oembed",
            params={"sessionid": "sid", "url": "https://example.com/p/abc"},
        )
    assert response.status_code == 200
    assert response.json()["version"] == "1.0"


@pytest.mark.asyncio
async def test_media_like_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/media/like", data={"sessionid": "sid", "media_id": "m1"}
        )
    assert response.status_code == 200
    assert response.json() is True


@pytest.mark.asyncio
async def test_media_unlike_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(
            "/media/like", params={"sessionid": "sid", "media_id": "m1"}
        )
    assert response.status_code == 200
    assert response.json() is True


@pytest.mark.asyncio
async def test_media_seen_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/media/seen",
            data={"sessionid": "sid", "media_ids": ["m1", "m2"]},
        )
    assert response.status_code == 200
    assert response.json() is True


@pytest.mark.asyncio
async def test_media_likers_returns_user_list(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/media/likers", params={"sessionid": "sid", "media_id": "m1"}
        )
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_media_archive_and_unarchive(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        archive = await ac.post(
            "/media/archive",
            data={"sessionid": "sid", "media_id": "m1", "revert": "true"},
        )
        unarchive = await ac.delete(
            "/media/archive", params={"sessionid": "sid", "media_id": "m1"}
        )
    assert archive.status_code == 200 and archive.json() is True
    assert unarchive.status_code == 200 and unarchive.json() is True
    assert ("media_archive", "m1", True) in storage.client.calls
    assert ("media_unarchive", "m1") in storage.client.calls


# Story routes
@pytest.mark.asyncio
async def test_story_user_stories_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/story/user/stories", params={"sessionid": "sid", "user_id": "1"}
        )
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_story_info_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/story/info", params={"sessionid": "sid", "story_pk": "1"}
        )
    assert response.status_code == 200
    assert str(response.json()["pk"]) == "1"


@pytest.mark.asyncio
async def test_story_delete_returns_true(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(
            "/story", params={"sessionid": "sid", "story_pk": "1"}
        )
    assert response.status_code == 200
    assert response.json() is True


@pytest.mark.asyncio
async def test_story_seen_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/story/seen",
            data={"sessionid": "sid", "story_pks": ["1", "2"]},
        )
    assert response.status_code == 200
    assert response.json() is True


@pytest.mark.asyncio
async def test_story_like_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/story/like",
            data={"sessionid": "sid", "story_id": "s1", "revert": "false"},
        )
    assert response.status_code == 200
    assert response.json() is True
    assert ("story_like", "s1", False) in storage.client.calls


@pytest.mark.asyncio
async def test_story_unlike_uses_story_id_not_undefined_name(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(
            "/story/like", params={"sessionid": "sid", "story_id": "s1"}
        )
    assert response.status_code == 200
    assert response.json() is True
    assert storage.client.story_unliked == "s1"


@pytest.mark.asyncio
async def test_story_download_returns_path_when_returnfile_false(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/story/download",
            params={"sessionid": "sid", "story_pk": "1", "returnFile": "false"},
        )
    assert response.status_code == 200
    assert response.json().endswith("test_media_story_routes.py")


@pytest.mark.asyncio
async def test_story_download_returns_file_when_returnfile_true(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/story/download", params={"sessionid": "sid", "story_pk": "1"}
        )
    assert response.status_code == 200
    assert b"import pytest" in response.content


@pytest.mark.asyncio
async def test_story_download_by_url_returns_path_when_returnfile_false(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/story/download/by/url",
            params={"sessionid": "sid", "url": "https://x/y", "returnFile": "false"},
        )
    assert response.status_code == 200
    assert response.json().endswith("test_media_story_routes.py")


@pytest.mark.asyncio
async def test_story_download_by_url_returns_file_when_returnfile_true(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/story/download/by/url",
            params={"sessionid": "sid", "url": "https://x/y"},
        )
    assert response.status_code == 200
    assert b"import pytest" in response.content
