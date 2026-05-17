import json
import types
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

import helpers
import routers.clip as clip_router
import routers.igtv as igtv_router
import routers.photo as photo_router
import routers.story as story_router
import routers.video as video_router
from dependencies import get_clients
from main import app


def _user_short():
    return {"pk": "42", "username": "u", "full_name": "Full"}


def _media_payload():
    return {
        "pk": 1,
        "id": "1_42",
        "code": "abc",
        "taken_at": "2026-01-01T00:00:00+00:00",
        "media_type": 1,
        "user": _user_short(),
        "like_count": 0,
        "caption_text": "",
        "usertags": [],
        "sponsor_tags": [],
    }


def _story_payload():
    return {
        "pk": 1,
        "id": "1_42",
        "code": "abc",
        "taken_at": "2026-01-01T00:00:00+00:00",
        "media_type": 1,
        "user": _user_short(),
        "sponsor_tags": [],
        "mentions": [],
        "links": [],
        "hashtags": [],
        "locations": [],
        "stickers": [],
    }


class FakeClient:
    def __init__(self):
        self.calls = []

    # Downloads
    async def photo_download(self, media_pk, folder=""):
        self.calls.append(("photo_download", media_pk, str(folder)))
        return Path(__file__).resolve()

    async def photo_download_by_url(self, url, filename, folder):
        self.calls.append(("photo_download_by_url", url, filename, str(folder)))
        return Path(__file__).resolve()

    async def video_download(self, media_pk, folder=""):
        self.calls.append(("video_download", media_pk, str(folder)))
        return Path(__file__).resolve()

    async def video_download_by_url(self, url, filename, folder):
        self.calls.append(("video_download_by_url", url, filename, str(folder)))
        return Path(__file__).resolve()

    async def clip_download(self, media_pk, folder=""):
        self.calls.append(("clip_download", media_pk, str(folder)))
        return Path(__file__).resolve()

    async def clip_download_by_url(self, url, filename, folder):
        self.calls.append(("clip_download_by_url", url, filename, str(folder)))
        return Path(__file__).resolve()

    async def igtv_download(self, media_pk, folder=""):
        self.calls.append(("igtv_download", media_pk, str(folder)))
        return Path(__file__).resolve()

    async def igtv_download_by_url(self, url, filename, folder):
        self.calls.append(("igtv_download_by_url", url, filename, str(folder)))
        return Path(__file__).resolve()

    async def album_download(self, media_pk, folder=""):
        self.calls.append(("album_download", media_pk, str(folder)))
        return [Path(__file__).resolve(), Path(__file__).resolve()]

    async def album_download_by_urls(self, urls, folder):
        self.calls.append(("album_download_by_urls", tuple(urls), str(folder)))
        return [Path(__file__).resolve()]

    # Uploads (called from helpers)
    async def photo_upload(self, path, **kwargs):
        self.calls.append(("photo_upload", path, kwargs))
        return _media_payload()

    async def video_upload(self, path, **kwargs):
        self.calls.append(("video_upload", path, kwargs))
        return _media_payload()

    async def album_upload(self, paths, **kwargs):
        self.calls.append(("album_upload", tuple(paths), kwargs))
        return _media_payload()

    async def igtv_upload(self, path, **kwargs):
        self.calls.append(("igtv_upload", path, kwargs))
        return _media_payload()

    async def clip_upload(self, path, **kwargs):
        self.calls.append(("clip_upload", path, kwargs))
        return _media_payload()

    async def photo_upload_to_story(self, path, **kwargs):
        self.calls.append(("photo_upload_to_story", path, kwargs))
        return _story_payload()

    async def video_upload_to_story(self, path, **kwargs):
        self.calls.append(("video_upload_to_story", path, kwargs))
        return _story_payload()


class FakeStorage:
    def __init__(self):
        self.client = FakeClient()

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


@pytest.fixture
def fake_requests(monkeypatch):
    """Replace requests.get with a fake that returns a small byte payload."""
    class FakeResponse:
        def __init__(self, content):
            self.content = content

    def fake_get(url, *args, **kwargs):
        return FakeResponse(b"fake-bytes")

    monkeypatch.setattr(photo_router, "requests", types.SimpleNamespace(get=fake_get))
    monkeypatch.setattr(video_router, "requests", types.SimpleNamespace(get=fake_get))
    monkeypatch.setattr(clip_router, "requests", types.SimpleNamespace(get=fake_get))
    monkeypatch.setattr(igtv_router, "requests", types.SimpleNamespace(get=fake_get))
    monkeypatch.setattr(story_router, "requests", types.SimpleNamespace(get=fake_get))


@pytest.fixture
def fake_storybuilder(monkeypatch):
    class FakeVideo:
        def __init__(self, path):
            self.path = path

    class FakeStoryBuilder:
        def __init__(self, path, caption, mentions, bgpath=None):
            self.path = path
            self.caption = caption
            self.mentions = mentions

        def photo(self, duration):
            return FakeVideo(self.path)

        def video(self, duration):
            return FakeVideo(self.path)

    monkeypatch.setattr(helpers, "StoryBuilder", FakeStoryBuilder)


# Photo routes
@pytest.mark.asyncio
async def test_photo_download_returns_path_when_returnfile_false(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/photo/download",
            params={"sessionid": "sid", "media_pk": "1", "returnFile": "false"},
        )
    assert response.status_code == 200
    assert response.json().endswith("test_upload_download_routes.py")


@pytest.mark.asyncio
async def test_photo_download_returns_file_when_returnfile_true(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/photo/download",
            params={"sessionid": "sid", "media_pk": "1"},
        )
    assert response.status_code == 200
    assert b"import pytest" in response.content


@pytest.mark.asyncio
async def test_photo_download_by_url_returns_path_when_returnfile_false(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/photo/download/by/url",
            params={
                "sessionid": "sid",
                "url": "https://x/y.jpg",
                "returnFile": "false",
            },
        )
    assert response.status_code == 200
    assert response.json().endswith("test_upload_download_routes.py")


@pytest.mark.asyncio
async def test_photo_download_by_url_returns_file_when_returnfile_true(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/photo/download/by/url",
            params={"sessionid": "sid", "url": "https://x/y.jpg"},
        )
    assert response.status_code == 200
    assert b"import pytest" in response.content


@pytest.mark.asyncio
async def test_photo_upload_uses_helper(storage):
    usertag = json.dumps({"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/photo/upload",
            data={"sessionid": "sid", "caption": "hi", "usertags": usertag},
            files={"file": ("a.jpg", b"img-bytes", "image/jpeg")},
        )
    assert response.status_code == 200
    assert any(call[0] == "photo_upload" for call in storage.client.calls)


@pytest.mark.asyncio
async def test_photo_upload_by_url_uses_helper(storage, fake_requests):
    usertag = json.dumps({"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/photo/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/photo.jpg",
                "caption": "hello",
                "usertags": usertag,
            },
        )
    assert response.status_code == 200
    assert any(call[0] == "photo_upload" for call in storage.client.calls)


@pytest.mark.asyncio
async def test_photo_upload_to_story_as_photo(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/story/upload",
            data={"sessionid": "sid", "caption": "hi", "as_video": "false"},
            files={"file": ("a.jpg", b"img-bytes", "image/jpeg")},
        )
    assert response.status_code == 200
    assert any(call[0] == "photo_upload_to_story" for call in storage.client.calls)


@pytest.mark.asyncio
async def test_photo_upload_to_story_as_video(storage, fake_storybuilder):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/story/upload",
            data={"sessionid": "sid", "caption": "hi", "as_video": "true"},
            files={"file": ("a.jpg", b"img-bytes", "image/jpeg")},
        )
    assert response.status_code == 200
    assert any(call[0] == "video_upload_to_story" for call in storage.client.calls)


@pytest.mark.asyncio
async def test_photo_upload_to_story_by_url_as_photo(storage, fake_requests):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/story/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/photo.jpg",
                "as_video": "false",
            },
        )
    assert response.status_code == 200
    assert any(call[0] == "photo_upload_to_story" for call in storage.client.calls)


@pytest.mark.asyncio
async def test_photo_upload_to_story_by_url_as_video(storage, fake_requests, fake_storybuilder):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/story/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/photo.jpg",
                "as_video": "true",
            },
        )
    assert response.status_code == 200
    assert any(call[0] == "video_upload_to_story" for call in storage.client.calls)


@pytest.mark.asyncio
async def test_story_upload_by_url_accepts_json_mentions(storage, fake_requests):
    mention = json.dumps([{"user": {"pk": "42", "username": "u", "full_name": "Full"}}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/story/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/photo.jpg",
                "mentions": mention,
            },
        )
    assert response.status_code == 200
    story_call = next(call for call in storage.client.calls if call[0] == "photo_upload_to_story")
    mention_model = story_call[2]["mentions"][0]
    assert mention_model.user.pk == "42"


@pytest.mark.asyncio
async def test_story_upload_by_url_rejects_invalid_json_mentions(storage, fake_requests):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/story/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/photo.jpg",
                "mentions": "{bad-json",
            },
        )
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid JSON object for form field 'mentions'"


# Video routes
@pytest.mark.asyncio
async def test_video_download_returns_path_when_returnfile_false(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/video/download",
            params={"sessionid": "sid", "media_pk": "1", "returnFile": "false"},
        )
    assert response.status_code == 200
    assert response.json().endswith("test_upload_download_routes.py")


@pytest.mark.asyncio
async def test_video_download_returns_file_when_returnfile_true(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/video/download",
            params={"sessionid": "sid", "media_pk": "1"},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_video_download_by_url_returns_path_when_returnfile_false(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/video/download/by/url",
            params={
                "sessionid": "sid",
                "url": "https://x/y.mp4",
                "returnFile": "false",
            },
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_video_download_by_url_returns_file_when_returnfile_true(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/video/download/by/url",
            params={"sessionid": "sid", "url": "https://x/y.mp4"},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_video_upload_with_and_without_thumbnail(storage):
    usertag = json.dumps({"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        no_thumb = await ac.post(
            "/video/upload",
            data={"sessionid": "sid", "caption": "hi", "usertags": usertag},
            files={"file": ("a.mp4", b"vid-bytes", "video/mp4")},
        )
        with_thumb = await ac.post(
            "/video/upload",
            data={"sessionid": "sid", "caption": "hi"},
            files=[
                ("file", ("a.mp4", b"vid-bytes", "video/mp4")),
                ("thumbnail", ("t.jpg", b"thumb-bytes", "image/jpeg")),
            ],
        )
    assert no_thumb.status_code == 200
    assert with_thumb.status_code == 200
    upload_calls = [c for c in storage.client.calls if c[0] == "video_upload"]
    assert len(upload_calls) == 2


@pytest.mark.asyncio
async def test_video_upload_by_url_with_and_without_thumbnail(storage, fake_requests):
    usertag = json.dumps({"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        no_thumb = await ac.post(
            "/video/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/v.mp4",
                "caption": "hi",
                "usertags": usertag,
            },
        )
        with_thumb = await ac.post(
            "/video/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/v.mp4",
                "caption": "hi",
            },
            files=[("thumbnail", ("t.jpg", b"thumb-bytes", "image/jpeg"))],
        )
    assert no_thumb.status_code == 200
    assert with_thumb.status_code == 200


@pytest.mark.asyncio
async def test_story_upload_video(storage, fake_storybuilder):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/story/upload",
            data={"sessionid": "sid", "caption": "hi"},
            files={"file": ("a.mp4", b"vid-bytes", "video/mp4")},
        )
    assert response.status_code == 200
    assert any(call[0] == "video_upload_to_story" for call in storage.client.calls)


@pytest.mark.asyncio
async def test_story_upload_video_by_url(storage, fake_requests, fake_storybuilder):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/story/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/v.mp4",
                "caption": "hi",
            },
        )
    assert response.status_code == 200


# Clip routes
@pytest.mark.asyncio
async def test_clip_download_routes_both_returnfile_modes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        path_resp = await ac.get(
            "/clip/download",
            params={"sessionid": "sid", "media_pk": "1", "returnFile": "false"},
        )
        file_resp = await ac.get(
            "/clip/download",
            params={"sessionid": "sid", "media_pk": "1"},
        )
    assert path_resp.status_code == 200
    assert file_resp.status_code == 200
    assert path_resp.json().endswith("test_upload_download_routes.py")


@pytest.mark.asyncio
async def test_clip_download_by_url_both_returnfile_modes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        path_resp = await ac.get(
            "/clip/download/by/url",
            params={
                "sessionid": "sid",
                "url": "https://x/y.mp4",
                "returnFile": "false",
            },
        )
        file_resp = await ac.get(
            "/clip/download/by/url",
            params={"sessionid": "sid", "url": "https://x/y.mp4"},
        )
    assert path_resp.status_code == 200
    assert file_resp.status_code == 200


@pytest.mark.asyncio
async def test_clip_upload_with_and_without_thumbnail(storage):
    usertag = json.dumps({"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        no_thumb = await ac.post(
            "/clip/upload",
            data={"sessionid": "sid", "caption": "hi", "usertags": usertag},
            files={"file": ("a.mp4", b"clip-bytes", "video/mp4")},
        )
        with_thumb = await ac.post(
            "/clip/upload",
            data={"sessionid": "sid", "caption": "hi"},
            files=[
                ("file", ("a.mp4", b"clip-bytes", "video/mp4")),
                ("thumbnail", ("t.jpg", b"thumb-bytes", "image/jpeg")),
            ],
        )
    assert no_thumb.status_code == 200
    assert with_thumb.status_code == 200
    upload_calls = [c for c in storage.client.calls if c[0] == "clip_upload"]
    assert len(upload_calls) == 2


@pytest.mark.asyncio
async def test_clip_upload_by_url_with_and_without_thumbnail(storage, fake_requests):
    usertag = json.dumps({"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        no_thumb = await ac.post(
            "/clip/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/c.mp4",
                "caption": "hi",
                "usertags": usertag,
            },
        )
        with_thumb = await ac.post(
            "/clip/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/c.mp4",
                "caption": "hi",
            },
            files=[("thumbnail", ("t.jpg", b"thumb-bytes", "image/jpeg"))],
        )
    assert no_thumb.status_code == 200
    assert with_thumb.status_code == 200


# IGTV routes
@pytest.mark.asyncio
async def test_igtv_download_routes_both_returnfile_modes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        path_resp = await ac.get(
            "/igtv/download",
            params={"sessionid": "sid", "media_pk": "1", "returnFile": "false"},
        )
        file_resp = await ac.get(
            "/igtv/download",
            params={"sessionid": "sid", "media_pk": "1"},
        )
    assert path_resp.status_code == 200
    assert file_resp.status_code == 200


@pytest.mark.asyncio
async def test_igtv_download_by_url_both_returnfile_modes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        path_resp = await ac.get(
            "/igtv/download/by/url",
            params={
                "sessionid": "sid",
                "url": "https://x/y.mp4",
                "returnFile": "false",
            },
        )
        file_resp = await ac.get(
            "/igtv/download/by/url",
            params={"sessionid": "sid", "url": "https://x/y.mp4"},
        )
    assert path_resp.status_code == 200
    assert file_resp.status_code == 200


@pytest.mark.asyncio
async def test_igtv_upload_with_and_without_thumbnail(storage):
    usertag = json.dumps({"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        no_thumb = await ac.post(
            "/igtv/upload",
            data={"sessionid": "sid", "title": "t", "caption": "hi", "usertags": usertag},
            files={"file": ("a.mp4", b"igtv-bytes", "video/mp4")},
        )
        with_thumb = await ac.post(
            "/igtv/upload",
            data={"sessionid": "sid", "title": "t", "caption": "hi"},
            files=[
                ("file", ("a.mp4", b"igtv-bytes", "video/mp4")),
                ("thumbnail", ("t.jpg", b"thumb-bytes", "image/jpeg")),
            ],
        )
    assert no_thumb.status_code == 200
    assert with_thumb.status_code == 200


@pytest.mark.asyncio
async def test_igtv_upload_by_url_with_and_without_thumbnail(storage, fake_requests):
    usertag = json.dumps({"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        no_thumb = await ac.post(
            "/igtv/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/i.mp4",
                "title": "t",
                "caption": "hi",
                "usertags": usertag,
            },
        )
        with_thumb = await ac.post(
            "/igtv/upload/by/url",
            data={
                "sessionid": "sid",
                "url": "https://example.com/i.mp4",
                "title": "t",
                "caption": "hi",
            },
            files=[("thumbnail", ("t.jpg", b"thumb-bytes", "image/jpeg"))],
        )
    assert no_thumb.status_code == 200
    assert with_thumb.status_code == 200


# Album routes
@pytest.mark.asyncio
async def test_album_download_returns_list(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/album/download",
            params={"sessionid": "sid", "media_pk": "1"},
        )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_album_download_by_urls_returns_list(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/album/download/by/urls",
            params={"sessionid": "sid", "urls": ["https://x/1.jpg", "https://x/2.jpg"]},
        )
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_album_upload(storage):
    usertag = json.dumps({"user": {"pk": 1, "username": "u", "full_name": "f"}, "x": 0.5, "y": 0.5})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/album/upload",
            data={"sessionid": "sid", "caption": "hi", "usertags": usertag},
            files=[
                ("files", ("a.jpg", b"img-1", "image/jpeg")),
                ("files", ("b.jpg", b"img-2", "image/jpeg")),
            ],
        )
    assert response.status_code == 200
    assert any(call[0] == "album_upload" for call in storage.client.calls)
