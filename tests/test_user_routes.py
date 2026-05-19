import pytest
from httpx import ASGITransport, AsyncClient

from aiograpi_rest.dependencies import get_clients
from aiograpi_rest.main import app


def _user_payload(pk="1", username="instagram"):
    return {
        "pk": pk,
        "username": username,
        "full_name": "Test",
        "is_private": False,
        "profile_pic_url": "https://example.com/p.jpg",
        "is_verified": True,
        "media_count": 0,
        "follower_count": 0,
        "following_count": 0,
        "is_business": False,
    }


def _user_short(pk):
    return {"pk": str(pk), "username": f"u{pk}", "full_name": "Full"}


class FakeClient:
    def __init__(self):
        self.calls = []

    async def user_followers_v1_chunk(self, user_id, max_amount=0, max_id=""):
        self.calls.append(("user_followers_v1_chunk", user_id, max_amount, max_id))
        return [_user_short(1), _user_short(2)], "next-followers"

    async def user_following_v1_chunk(self, user_id, max_amount=0, max_id=""):
        self.calls.append(("user_following_v1_chunk", user_id, max_amount, max_id))
        return [_user_short(3)], "next-following"

    async def user_info(self, user_id):
        self.calls.append(("user_info", user_id))
        return _user_payload(pk=str(user_id))

    async def user_info_by_username(self, username):
        self.calls.append(("user_info_by_username", username))
        return _user_payload(username=username)

    async def user_about_v1(self, user_id):
        self.calls.append(("user_about_v1", user_id))
        return {
            "username": "instagram",
            "is_verified": True,
            "country": "United States",
            "date": "October 2010",
            "former_usernames": "0",
        }

    async def user_follow(self, user_id):
        self.calls.append(("user_follow", user_id))
        return True

    async def user_unfollow(self, user_id):
        self.calls.append(("user_unfollow", user_id))
        return True

    async def user_id_from_username(self, username):
        self.calls.append(("user_id_from_username", username))
        return 42

    async def username_from_user_id(self, user_id):
        self.calls.append(("username_from_user_id", user_id))
        return "instagram"

    async def user_remove_follower(self, user_id):
        self.calls.append(("user_remove_follower", user_id))
        return True

    async def mute_posts_from_follow(self, user_id, revert=False):
        self.calls.append(("mute_posts_from_follow", user_id, revert))
        return True

    async def unmute_posts_from_follow(self, user_id):
        self.calls.append(("unmute_posts_from_follow", user_id))
        return True

    async def mute_stories_from_follow(self, user_id, revert=False):
        self.calls.append(("mute_stories_from_follow", user_id, revert))
        return True

    async def unmute_stories_from_follow(self, user_id):
        self.calls.append(("unmute_stories_from_follow", user_id))
        return True

    async def user_follow_request_approve(self, user_id):
        self.calls.append(("user_follow_request_approve", user_id))
        return True

    async def user_follow_request_decline(self, user_id):
        self.calls.append(("user_follow_request_decline", user_id))
        return True

    async def close_friend_add(self, user_id):
        self.calls.append(("close_friend_add", user_id))
        return True

    async def close_friend_remove(self, user_id):
        self.calls.append(("close_friend_remove", user_id))
        return True

    async def enable_posts_notifications(self, user_id):
        self.calls.append(("enable_posts_notifications", user_id))
        return True

    async def disable_posts_notifications(self, user_id):
        self.calls.append(("disable_posts_notifications", user_id))
        return True

    async def enable_stories_notifications(self, user_id):
        self.calls.append(("enable_stories_notifications", user_id))
        return True

    async def disable_stories_notifications(self, user_id):
        self.calls.append(("disable_stories_notifications", user_id))
        return True

    async def enable_reels_notifications(self, user_id):
        self.calls.append(("enable_reels_notifications", user_id))
        return True

    async def disable_reels_notifications(self, user_id):
        self.calls.append(("disable_reels_notifications", user_id))
        return True

    async def enable_videos_notifications(self, user_id):
        self.calls.append(("enable_videos_notifications", user_id))
        return True

    async def disable_videos_notifications(self, user_id):
        self.calls.append(("disable_videos_notifications", user_id))
        return True


class FakeStorage:
    def __init__(self):
        self.client_instance = FakeClient()

    async def get(self, sessionid):
        return self.client_instance

    def close(self):
        pass


@pytest.fixture
def storage():
    fake = FakeStorage()
    app.dependency_overrides[get_clients] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_user_followers_returns_paginated_items(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/user/followers",
            params={"sessionid": "sid", "user_id": "1", "amount": "5", "cursor": "cursor"},
        )
    assert response.status_code == 200
    assert response.json()["items"][0]["pk"] == "1"
    assert response.json()["next_cursor"] == "next-followers"
    assert ("user_followers_v1_chunk", "1", 5, "cursor") in storage.client_instance.calls


@pytest.mark.asyncio
async def test_user_following_returns_paginated_items(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/user/following",
            params={"sessionid": "sid", "user_id": "1", "use_cache": "false"},
        )
    assert response.status_code == 200
    assert response.json()["items"][0]["pk"] == "3"
    assert response.json()["next_cursor"] == "next-following"
    assert ("user_following_v1_chunk", "1", 50, "") in storage.client_instance.calls


@pytest.mark.asyncio
async def test_user_returns_profile_by_id(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/user",
            params={"sessionid": "sid", "user_id": "55"},
        )
    assert response.status_code == 200
    assert response.json()["pk"] == "55"
    assert ("user_info", "55") in storage.client_instance.calls


@pytest.mark.asyncio
async def test_user_returns_profile_by_username(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/user",
            params={"sessionid": "sid", "username": "instagram"},
        )
    assert response.status_code == 200
    assert response.json()["username"] == "instagram"
    assert ("user_info_by_username", "instagram") in storage.client_instance.calls


@pytest.mark.asyncio
async def test_user_rejects_missing_identifier(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/user", params={"sessionid": "sid"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Provide user_id or username"


@pytest.mark.asyncio
async def test_user_rejects_conflicting_identifiers(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/user",
            params={"sessionid": "sid", "user_id": "55", "username": "instagram"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "Provide either user_id or username, not both"


@pytest.mark.asyncio
async def test_user_about_returns_about_payload(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/user/about", params={"sessionid": "sid", "user_id": "25025320"}
        )

    assert response.status_code == 200
    assert response.json()["username"] == "instagram"
    assert response.json()["is_verified"] is True
    assert ("user_about_v1", "25025320") in storage.client_instance.calls


@pytest.mark.asyncio
async def test_user_about_normalizes_bool_country(storage):
    async def user_about_with_bool_country(user_id):
        storage.client_instance.calls.append(("user_about_v1", user_id))
        return {
            "username": "instagram",
            "is_verified": True,
            "country": True,
            "date": 2010,
            "former_usernames": "0",
        }

    storage.client_instance.user_about_v1 = user_about_with_bool_country

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/user/about", params={"sessionid": "sid", "user_id": "25025320"}
        )

    assert response.status_code == 200
    assert response.json()["country"] == ""
    assert response.json()["date"] == "2010"
    assert response.json()["username"] == "instagram"


@pytest.mark.asyncio
async def test_user_about_accepts_about_model(storage):
    from aiograpi.types import About

    async def user_about_model(user_id):
        storage.client_instance.calls.append(("user_about_v1", user_id))
        return About(username="instagram", country="United States")

    storage.client_instance.user_about_v1 = user_about_model

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/user/about", params={"sessionid": "sid", "user_id": "25025320"}
        )

    assert response.status_code == 200
    assert response.json()["country"] == "United States"
    assert response.json()["username"] == "instagram"


@pytest.mark.asyncio
async def test_user_about_falls_back_when_aiograpi_rejects_bool_country(storage):
    from aiograpi.types import About

    async def user_about_with_invalid_country(user_id):
        storage.client_instance.calls.append(("user_about_v1", user_id))
        storage.client_instance.last_json = {
            "layout": {"bloks_payload": {"data": [{"data": {"initial": True}}]}}
        }
        return About(country=True)

    storage.client_instance.user_about_v1 = user_about_with_invalid_country

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/user/about", params={"sessionid": "sid", "user_id": "25025320"}
        )

    assert response.status_code == 200
    assert response.json()["country"] == ""
    assert ("user_about_v1", "25025320") in storage.client_instance.calls


def test_extract_about_from_last_json_covers_bloks_fields():
    from aiograpi_rest.routers.user import _extract_about_from_last_json

    about = _extract_about_from_last_json(
        {
            "layout": {"bloks_payload": {"data": [{"data": {"initial": True}}]}},
            'username")': {"style": "bold"},
            'date_marker")': "Date joined",
            'date_value")': "February 2012",
            'former_marker")': "Former usernames",
            'skip")': "ignored",
            'former_value")': "0",
        }
    )

    assert about.country == ""
    assert about.date == "February 2012"
    assert about.former_usernames.startswith("0")
    assert about.username


@pytest.mark.asyncio
async def test_user_about_reraises_validation_without_last_json(storage):
    from aiograpi.types import About

    async def user_about_without_last_json(user_id):
        storage.client_instance.calls.append(("user_about_v1", user_id))
        return About(country=True)

    storage.client_instance.user_about_v1 = user_about_without_last_json
    transport = ASGITransport(app=app, raise_app_exceptions=False)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/user/about", params={"sessionid": "sid", "user_id": "25025320"}
        )

    assert response.status_code == 500
    assert response.json()["exc_type"] == "ValidationError"


@pytest.mark.asyncio
async def test_user_follow_awaits_client_method(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/user/follow", data={"sessionid": "sid", "user_id": "1"})

    assert response.status_code == 200
    assert response.json() is True
    assert ("user_follow", 1) in storage.client_instance.calls


@pytest.mark.asyncio
async def test_user_unfollow_awaits_client_method(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete("/user/follow", params={"sessionid": "sid", "user_id": "1"})
    assert response.status_code == 200
    assert ("user_unfollow", 1) in storage.client_instance.calls


@pytest.mark.asyncio
async def test_user_remove_follower_returns_true(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(
            "/user/follower",
            params={"sessionid": "sid", "user_id": "1"},
        )
    assert response.status_code == 200
    assert ("user_remove_follower", 1) in storage.client_instance.calls


@pytest.mark.asyncio
async def test_mute_and_unmute_posts_from_follow(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        mute = await ac.post(
            "/user/mute/posts",
            data={"sessionid": "sid", "user_id": "1", "revert": "true"},
        )
        unmute = await ac.delete(
            "/user/mute/posts",
            params={"sessionid": "sid", "user_id": "1"},
        )
    assert mute.status_code == 200 and mute.json() is True
    assert unmute.status_code == 200 and unmute.json() is True
    assert ("mute_posts_from_follow", 1, True) in storage.client_instance.calls
    assert ("unmute_posts_from_follow", 1) in storage.client_instance.calls


@pytest.mark.asyncio
async def test_mute_and_unmute_stories_from_follow(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        mute = await ac.post(
            "/user/mute/stories",
            data={"sessionid": "sid", "user_id": "1"},
        )
        unmute = await ac.delete(
            "/user/mute/stories",
            params={"sessionid": "sid", "user_id": "1"},
        )
    assert mute.status_code == 200 and mute.json() is True
    assert unmute.status_code == 200 and unmute.json() is True
    assert ("mute_stories_from_follow", 1, False) in storage.client_instance.calls
    assert ("unmute_stories_from_follow", 1) in storage.client_instance.calls


@pytest.mark.asyncio
async def test_account_follow_request_actions(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        approve = await ac.post(
            "/account/follow/request/approve",
            data={"sessionid": "sid", "user_id": "1"},
        )
        decline = await ac.delete(
            "/account/follow/request",
            params={"sessionid": "sid", "user_id": "1"},
        )

    assert approve.status_code == 200 and approve.json() is True
    assert decline.status_code == 200 and decline.json() is True
    assert ("user_follow_request_approve", 1) in storage.client_instance.calls
    assert ("user_follow_request_decline", 1) in storage.client_instance.calls


@pytest.mark.asyncio
async def test_close_friend_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        add = await ac.post("/user/close-friend", data={"sessionid": "sid", "user_id": "1"})
        remove = await ac.delete("/user/close-friend", params={"sessionid": "sid", "user_id": "1"})

    assert add.status_code == 200 and add.json() is True
    assert remove.status_code == 200 and remove.json() is True
    assert ("close_friend_add", 1) in storage.client_instance.calls
    assert ("close_friend_remove", 1) in storage.client_instance.calls


@pytest.mark.asyncio
async def test_user_notification_toggle_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        posts_on = await ac.post("/user/notifications/posts", data={"sessionid": "sid", "user_id": "1"})
        posts_off = await ac.delete("/user/notifications/posts", params={"sessionid": "sid", "user_id": "1"})
        stories_on = await ac.post("/user/notifications/stories", data={"sessionid": "sid", "user_id": "1"})
        stories_off = await ac.delete("/user/notifications/stories", params={"sessionid": "sid", "user_id": "1"})
        reels_on = await ac.post("/user/notifications/reels", data={"sessionid": "sid", "user_id": "1"})
        reels_off = await ac.delete("/user/notifications/reels", params={"sessionid": "sid", "user_id": "1"})
        videos_on = await ac.post("/user/notifications/videos", data={"sessionid": "sid", "user_id": "1"})
        videos_off = await ac.delete("/user/notifications/videos", params={"sessionid": "sid", "user_id": "1"})

    assert posts_on.status_code == 200 and posts_off.status_code == 200
    assert stories_on.status_code == 200 and stories_off.status_code == 200
    assert reels_on.status_code == 200 and reels_off.status_code == 200
    assert videos_on.status_code == 200 and videos_off.status_code == 200
    assert ("enable_posts_notifications", 1) in storage.client_instance.calls
    assert ("disable_posts_notifications", 1) in storage.client_instance.calls
    assert ("enable_stories_notifications", 1) in storage.client_instance.calls
    assert ("disable_stories_notifications", 1) in storage.client_instance.calls
    assert ("enable_reels_notifications", 1) in storage.client_instance.calls
    assert ("disable_reels_notifications", 1) in storage.client_instance.calls
    assert ("enable_videos_notifications", 1) in storage.client_instance.calls
    assert ("disable_videos_notifications", 1) in storage.client_instance.calls
