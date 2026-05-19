from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from aiograpi_rest.dependencies import get_clients
from aiograpi_rest.main import app


def _user_short(pk=1):
    return {"pk": str(pk), "username": f"user{pk}", "full_name": f"User {pk}"}


def _media_payload(pk=1):
    return {
        "pk": pk,
        "id": f"{pk}_1",
        "code": "abc",
        "taken_at": "2026-01-01T00:00:00+00:00",
        "media_type": 1,
        "user": _user_short(1),
        "like_count": 0,
        "caption_text": "",
        "usertags": [],
        "sponsor_tags": [],
    }


def _comment_payload(pk="10"):
    return {
        "pk": pk,
        "text": "hello",
        "user": _user_short(1),
        "created_at_utc": "2026-01-01T00:00:00+00:00",
        "content_type": "comment",
        "status": "Active",
    }


def _viewer_payload(pk=1):
    return {**_user_short(pk), "has_liked": True}


def _story_archive_day_payload(day_id="day1"):
    return {
        "id": day_id,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "media_count": 1,
        "reel_type": "archive",
    }


def _direct_message_payload(message_id="m1"):
    return {
        "id": message_id,
        "thread_id": 100,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "item_type": "text",
        "text": "hello",
    }


def _direct_thread_payload(thread_id="100"):
    return {
        "pk": thread_id,
        "id": thread_id,
        "messages": [_direct_message_payload()],
        "users": [_user_short(1)],
        "admin_user_ids": [],
        "last_activity_at": "2026-01-01T00:00:00+00:00",
        "muted": False,
        "named": False,
        "canonical": True,
        "pending": False,
        "archived": False,
        "thread_type": "private",
        "thread_title": "Thread",
        "folder": 0,
        "vc_muted": False,
        "is_group": False,
        "mentions_muted": False,
        "approval_required_for_new_members": False,
        "input_mode": 0,
    }


class FakePaginationClient:
    def __init__(self):
        self.calls = []

    async def user_id_from_username(self, username):
        self.calls.append(("user_id_from_username", username))
        return 25025320

    async def user_info_by_username_v1(self, username):
        self.calls.append(("user_info_by_username_v1", username))
        return SimpleNamespace(pk="25025320")

    async def user_medias_paginated(self, user_id, amount=0, end_cursor=""):
        self.calls.append(("user_medias_paginated", user_id, amount, end_cursor))
        return [_media_payload(1)], "next-user-medias"

    async def user_medias_paginated_v1(self, user_id, amount=0, end_cursor=""):
        self.calls.append(("user_medias_paginated_v1", user_id, amount, end_cursor))
        return [_media_payload(1)], "next-user-medias"

    async def usertag_medias_paginated(self, user_id, amount=0, end_cursor=""):
        self.calls.append(("usertag_medias_paginated", user_id, amount, end_cursor))
        return [_media_payload(2)], "next-usertag-medias"

    async def user_clips_paginated_v1(self, user_id, amount=50, end_cursor=""):
        self.calls.append(("user_clips_paginated_v1", user_id, amount, end_cursor))
        return [_media_payload(3)], "next-user-clips"

    async def user_videos_paginated_v1(self, user_id, amount=50, end_cursor=""):
        self.calls.append(("user_videos_paginated_v1", user_id, amount, end_cursor))
        return [_media_payload(4)], "next-user-videos"

    async def user_followers_v1_chunk(self, user_id, max_amount=0, max_id=""):
        self.calls.append(("user_followers_v1_chunk", user_id, max_amount, max_id))
        return [_user_short(1)], "next-followers"

    async def user_following_v1_chunk(self, user_id, max_amount=0, max_id=""):
        self.calls.append(("user_following_v1_chunk", user_id, max_amount, max_id))
        return [_user_short(2)], "next-following"

    async def user_follow_requests_chunk(self, max_amount=0, max_id=""):
        self.calls.append(("user_follow_requests_chunk", max_amount, max_id))
        return [_user_short(3)], "next-follow-requests"

    async def hashtag_medias_v1_chunk(self, name, max_amount=27, tab_key="", max_id=None):
        self.calls.append(("hashtag_medias_v1_chunk", name, max_amount, tab_key, max_id))
        return [_media_payload(5)], f"next-hashtag-{tab_key}"

    async def location_medias_v1_chunk(self, location_pk, max_amount=63, tab_key="", max_id=None):
        self.calls.append(("location_medias_v1_chunk", location_pk, max_amount, tab_key, max_id))
        return [_media_payload(6)], f"next-location-{tab_key}"

    async def media_comments_chunk(self, media_id, max_amount=20, min_id=None):
        self.calls.append(("media_comments_chunk", media_id, max_amount, min_id))
        return [_comment_payload()], "next-comments"

    async def story_viewers_chunk(self, story_pk, max_amount=0, max_id=""):
        self.calls.append(("story_viewers_chunk", story_pk, max_amount, max_id))
        return [_viewer_payload(1)], "next-story-viewers"

    async def archive_story_days_paginated_v1(
        self,
        amount=0,
        end_cursor="",
        include_memories=True,
        reel_id="",
    ):
        self.calls.append(("archive_story_days_paginated_v1", amount, end_cursor, include_memories, reel_id))
        return [_story_archive_day_payload()], "next-story-archive"

    async def direct_threads_chunk(
        self,
        selected_filter="",
        box="",
        thread_message_limit=None,
        cursor=None,
    ):
        self.calls.append(("direct_threads_chunk", selected_filter, box, thread_message_limit, cursor))
        return [_direct_thread_payload()], "next-direct-inbox"


class FakeStorage:
    def __init__(self):
        self.client = FakePaginationClient()

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


async def _get(path, params):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        return await ac.get(path, params={"sessionid": "sid", **params})


@pytest.mark.asyncio
async def test_media_read_list_routes_return_items_and_next_cursor(storage):
    routes = [
        ("/user/posts", {"user_id": "10", "amount": "7", "cursor": "m1"}, "next-user-medias"),
        ("/user/tagged/posts", {"user_id": "10", "amount": "8", "cursor": "t1"}, "next-usertag-medias"),
        ("/user/reels", {"user_id": "10", "amount": "9", "cursor": "c1"}, "next-user-clips"),
        ("/user/videos", {"user_id": "10", "amount": "10", "cursor": "v1"}, "next-user-videos"),
    ]

    for path, params, next_cursor in routes:
        response = await _get(path, params)
        assert response.status_code == 200
        assert response.json()["items"][0]["pk"] in {1, 2, 3, 4}
        assert response.json()["next_cursor"] == next_cursor
        assert "end_cursor" not in response.json()

    assert ("user_medias_paginated_v1", "10", 7, "m1") in storage.client.calls
    assert ("usertag_medias_paginated", "10", 8, "t1") in storage.client.calls
    assert ("user_clips_paginated_v1", "10", 9, "c1") in storage.client.calls
    assert ("user_videos_paginated_v1", "10", 10, "v1") in storage.client.calls


@pytest.mark.asyncio
async def test_user_media_read_list_routes_resolve_username(storage):
    routes = [
        ("/user/posts", {"username": "instagram", "amount": "7"}, "user_medias_paginated_v1"),
        ("/user/tagged/posts", {"username": "instagram", "amount": "8"}, "usertag_medias_paginated"),
        ("/user/reels", {"username": "instagram", "amount": "9"}, "user_clips_paginated_v1"),
        ("/user/videos", {"username": "instagram", "amount": "10"}, "user_videos_paginated_v1"),
    ]

    for path, params, method_name in routes:
        response = await _get(path, params)
        assert response.status_code == 200
        assert response.json()["items"]
        assert any(call[0] == method_name and call[1] == "25025320" for call in storage.client.calls)

    assert storage.client.calls.count(("user_info_by_username_v1", "instagram")) == 4
    assert not any(call[0] == "user_id_from_username" for call in storage.client.calls)


@pytest.mark.asyncio
async def test_user_media_read_list_routes_resolve_username_in_user_id(storage):
    checks = [
        ("/user/posts", "user_medias_paginated_v1"),
        ("/user/reels", "user_clips_paginated_v1"),
        ("/user/videos", "user_videos_paginated_v1"),
    ]

    for path, method_name in checks:
        response = await _get(path, {"user_id": "iarijitbiswas", "amount": "2"})
        assert response.status_code == 200
        assert response.json()["items"]
        assert ("user_info_by_username_v1", "iarijitbiswas") in storage.client.calls
        assert any(call[0] == method_name and call[1] == "25025320" and call[2] == 2 for call in storage.client.calls)

    assert not any(call[0] == "user_id_from_username" for call in storage.client.calls)


@pytest.mark.asyncio
async def test_user_media_read_list_routes_require_one_user_identifier(storage):
    missing = await _get("/user/posts", {"amount": "2"})
    both = await _get("/user/posts", {"user_id": "10", "username": "instagram", "amount": "2"})

    assert missing.status_code == 422
    assert missing.json()["detail"] == "Provide user_id or username"
    assert both.status_code == 422
    assert both.json()["detail"] == "Provide either user_id or username, not both"


@pytest.mark.asyncio
async def test_user_discovery_story_and_direct_list_routes_return_items_and_next_cursor(storage):
    checks = [
        ("/user/followers", {"user_id": "10", "amount": "11", "cursor": "f1"}, "next-followers"),
        ("/user/following", {"user_id": "10", "amount": "12", "cursor": "g1"}, "next-following"),
        ("/account/follow/requests", {"amount": "13", "cursor": "r1"}, "next-follow-requests"),
        ("/hashtag/media/top", {"name": "python", "amount": "14", "cursor": "ht1"}, "next-hashtag-top"),
        ("/hashtag/media/recent", {"name": "python", "amount": "15", "cursor": "hr1"}, "next-hashtag-recent"),
        ("/location/media/top", {"location_pk": "1", "amount": "16", "cursor": "lt1"}, "next-location-ranked"),
        ("/location/media/recent", {"location_pk": "1", "amount": "17", "cursor": "lr1"}, "next-location-recent"),
        ("/media/comments", {"media_id": "m1", "amount": "18", "cursor": "mc1"}, "next-comments"),
        ("/story/viewers", {"story_pk": "100", "amount": "18", "cursor": "sv1"}, "next-story-viewers"),
        (
            "/story/archive",
            {"amount": "19", "cursor": "sa1", "include_memories": "false", "reel_id": "archive"},
            "next-story-archive",
        ),
        (
            "/direct/inbox",
            {"selected_filter": "unread", "box": "primary", "thread_message_limit": "3", "cursor": "di1"},
            "next-direct-inbox",
        ),
    ]

    for path, params, next_cursor in checks:
        response = await _get(path, params)
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["next_cursor"] == next_cursor

    assert ("user_follow_requests_chunk", 13, "r1") in storage.client.calls
    assert ("hashtag_medias_v1_chunk", "python", 14, "top", "ht1") in storage.client.calls
    assert ("hashtag_medias_v1_chunk", "python", 15, "recent", "hr1") in storage.client.calls
    assert ("location_medias_v1_chunk", 1, 16, "ranked", "lt1") in storage.client.calls
    assert ("location_medias_v1_chunk", 1, 17, "recent", "lr1") in storage.client.calls
    assert ("media_comments_chunk", "m1", 18, "mc1") in storage.client.calls
    assert ("story_viewers_chunk", "100", 18, "sv1") in storage.client.calls
    assert ("archive_story_days_paginated_v1", 19, "sa1", False, "archive") in storage.client.calls
    assert ("direct_threads_chunk", "unread", "primary", 3, "di1") in storage.client.calls


@pytest.mark.asyncio
async def test_openapi_read_list_routes_use_page_schemas_and_cursor_parameter():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    expected_refs = {
        "/user/posts": "MediaPage",
        "/user/tagged/posts": "MediaPage",
        "/user/reels": "MediaPage",
        "/user/videos": "MediaPage",
        "/user/followers": "UserShortPage",
        "/user/following": "UserShortPage",
        "/account/follow/requests": "UserShortPage",
        "/hashtag/media/top": "MediaPage",
        "/hashtag/media/recent": "MediaPage",
        "/location/media/top": "MediaPage",
        "/location/media/recent": "MediaPage",
        "/media/comments": "CommentPage",
        "/story/viewers": "ViewerPage",
        "/story/archive": "StoryArchiveDayPage",
        "/direct/inbox": "DirectThreadPage",
    }
    for path, schema_name in expected_refs.items():
        operation = schema["paths"][path]["get"]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{schema_name}"
        }
        parameter_names = {parameter["name"] for parameter in operation.get("parameters", [])}
        assert "cursor" in parameter_names
        assert "end_cursor" not in parameter_names

    assert "/media/user/medias" not in schema["paths"]
    assert "/media/usertag/medias" not in schema["paths"]
    assert "/media/user/clips" not in schema["paths"]
    assert "/media/user/videos" not in schema["paths"]
    assert "/user/clips" not in schema["paths"]
    assert "/user/video" not in schema["paths"]
    assert "/user/media" not in schema["paths"]
    assert "/user/tagged/media" not in schema["paths"]
