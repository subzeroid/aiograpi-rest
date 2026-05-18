from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from aiograpi_rest.dependencies import get_clients
from aiograpi_rest.main import app


def _user_short(pk=1):
    return {"pk": str(pk), "username": f"user{pk}", "full_name": f"User {pk}"}


def _account_payload():
    return {
        "pk": "1",
        "username": "account",
        "full_name": "Account",
        "is_private": False,
        "profile_pic_url": "https://example.com/avatar.jpg",
        "is_verified": False,
        "is_business": False,
    }


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


def _direct_message_payload(message_id="m1"):
    return {
        "id": message_id,
        "thread_id": 100,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "item_type": "text",
        "text": "hello",
    }


def _direct_thread_payload():
    return {
        "pk": "100",
        "id": "100",
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


def _location_payload(pk=1):
    return {"pk": pk, "name": "Location", "lat": 1.0, "lng": 2.0}


def _relationship_payload(user_id="1"):
    return {
        "user_id": user_id,
        "blocking": False,
        "followed_by": False,
        "following": True,
        "incoming_request": False,
        "is_bestie": False,
        "is_blocking_reel": False,
        "is_muting_reel": False,
        "is_private": False,
        "is_restricted": False,
        "muting": False,
        "outgoing_request": False,
    }


def _highlight_payload(pk="h1"):
    return {
        "pk": pk,
        "id": pk,
        "latest_reel_media": 1,
        "cover_media": {},
        "user": _user_short(1),
        "title": "Highlight",
        "created_at": "2026-01-01T00:00:00+00:00",
        "is_pinned_highlight": False,
        "media_count": 1,
        "media_ids": [1],
        "items": [],
    }


def _note_payload(note_id="n1"):
    return {
        "id": note_id,
        "text": "note",
        "user_id": "1",
        "user": _user_short(1),
        "audience": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "expires_at": "2026-01-02T00:00:00+00:00",
        "is_emoji_only": False,
        "has_translation": False,
        "note_style": 0,
    }


class FakeExpandedClient:
    def __init__(self):
        self.calls = []

    async def account_info(self):
        self.calls.append(("account_info",))
        return _account_payload()

    async def account_edit(self, **data):
        self.calls.append(("account_edit", data))
        payload = _account_payload()
        payload.update({key: value for key, value in data.items() if value is not None})
        return payload

    async def account_change_picture(self, path):
        self.calls.append(("account_change_picture", Path(path).suffix))
        return _user_short(1)

    async def account_set_private(self):
        self.calls.append(("account_set_private",))
        return True

    async def account_set_public(self):
        self.calls.append(("account_set_public",))
        return True

    async def media_comments(self, media_id, amount=20):
        self.calls.append(("media_comments", media_id, amount))
        return [_comment_payload()]

    async def media_comment(self, media_id, text, replied_to_comment_id=None):
        self.calls.append(("media_comment", media_id, text, replied_to_comment_id))
        return _comment_payload()

    async def comment_bulk_delete(self, media_id, comment_pks):
        self.calls.append(("comment_bulk_delete", media_id, comment_pks))
        return True

    async def media_comment_replies(self, media_id, comment_id, amount=0):
        self.calls.append(("media_comment_replies", media_id, comment_id, amount))
        return [_comment_payload("11")]

    async def comment_like(self, comment_pk, revert=False):
        self.calls.append(("comment_like", comment_pk, revert))
        return True

    async def comment_unlike(self, comment_pk):
        self.calls.append(("comment_unlike", comment_pk))
        return True

    async def liked_medias(self, amount=21, last_media_pk=0):
        self.calls.append(("liked_medias", amount, last_media_pk))
        return [_media_payload()]

    async def media_save(self, media_id, collection_pk=None, revert=False):
        self.calls.append(("media_save", media_id, collection_pk, revert))
        return True

    async def media_unsave(self, media_id, collection_pk=None):
        self.calls.append(("media_unsave", media_id, collection_pk))
        return True

    async def media_pin(self, media_pk, revert=False):
        self.calls.append(("media_pin", media_pk, revert))
        return True

    async def media_unpin(self, media_pk):
        self.calls.append(("media_unpin", media_pk))
        return True

    async def direct_threads(self, amount=20, selected_filter="", box="", thread_message_limit=None):
        self.calls.append(("direct_threads", amount, selected_filter, box, thread_message_limit))
        return [_direct_thread_payload()]

    async def direct_thread(self, thread_id, amount=20):
        self.calls.append(("direct_thread", thread_id, amount))
        return _direct_thread_payload()

    async def direct_thread_create(self, user_ids, title=""):
        self.calls.append(("direct_thread_create", user_ids, title))
        return "100"

    async def direct_send(self, text, user_ids=None, thread_ids=None, send_attribute="message_button"):
        self.calls.append(("direct_send", text, user_ids or [], thread_ids or [], send_attribute))
        return _direct_message_payload()

    async def direct_message_delete(self, thread_id, message_id):
        self.calls.append(("direct_message_delete", thread_id, message_id))
        return True

    async def direct_message_seen(self, thread_id, message_id):
        self.calls.append(("direct_message_seen", thread_id, message_id))
        return True

    async def hashtag_info(self, name):
        self.calls.append(("hashtag_info", name))
        return {"id": "tag1", "name": name, "media_count": 1}

    async def hashtag_medias_top(self, name, amount=9):
        self.calls.append(("hashtag_medias_top", name, amount))
        return [_media_payload()]

    async def hashtag_medias_recent(self, name, amount=27):
        self.calls.append(("hashtag_medias_recent", name, amount))
        return [_media_payload()]

    async def hashtag_follow(self, hashtag, unfollow=False):
        self.calls.append(("hashtag_follow", hashtag, unfollow))
        return True

    async def hashtag_unfollow(self, hashtag):
        self.calls.append(("hashtag_unfollow", hashtag))
        return True

    async def location_search(self, lat, lng):
        self.calls.append(("location_search", lat, lng))
        return [_location_payload()]

    async def location_search_name(self, name):
        self.calls.append(("location_search_name", name))
        return [_location_payload()]

    async def location_info(self, location_pk):
        self.calls.append(("location_info", location_pk))
        return _location_payload(location_pk)

    async def location_medias_top(self, location_pk, amount=27, sleep=0.5):
        self.calls.append(("location_medias_top", location_pk, amount, sleep))
        return [_media_payload()]

    async def location_medias_recent(self, location_pk, amount=63, sleep=0.5):
        self.calls.append(("location_medias_recent", location_pk, amount, sleep))
        return [_media_payload()]

    async def search_users(self, query):
        self.calls.append(("search_users", query))
        return [_user_short(1)]

    async def user_friendship_v1(self, user_id):
        self.calls.append(("user_friendship_v1", user_id))
        return _relationship_payload(user_id)

    async def user_block(self, user_id, surface="profile"):
        self.calls.append(("user_block", user_id, surface))
        return True

    async def user_unblock(self, user_id, surface="profile"):
        self.calls.append(("user_unblock", user_id, surface))
        return True

    async def user_follow_requests(self, amount=0):
        self.calls.append(("user_follow_requests", amount))
        return [_user_short(1)]

    async def user_highlights(self, user_id, amount=0):
        self.calls.append(("user_highlights", user_id, amount))
        return [_highlight_payload()]

    async def highlight_info(self, highlight_pk):
        self.calls.append(("highlight_info", highlight_pk))
        return _highlight_payload(highlight_pk)

    async def highlight_create(self, title, story_ids, cover_story_id="", crop_rect=None):
        self.calls.append(("highlight_create", title, story_ids, cover_story_id, crop_rect))
        return _highlight_payload()

    async def highlight_edit(self, highlight_pk, title="", cover=None, added_media_ids=None, removed_media_ids=None):
        self.calls.append(("highlight_edit", highlight_pk, title, cover or {}, added_media_ids or [], removed_media_ids or []))
        return _highlight_payload(highlight_pk)

    async def highlight_delete(self, highlight_pk):
        self.calls.append(("highlight_delete", highlight_pk))
        return True

    async def highlight_add_stories(self, highlight_pk, added_media_ids):
        self.calls.append(("highlight_add_stories", highlight_pk, added_media_ids))
        return _highlight_payload(highlight_pk)

    async def highlight_remove_stories(self, highlight_pk, removed_media_ids):
        self.calls.append(("highlight_remove_stories", highlight_pk, removed_media_ids))
        return _highlight_payload(highlight_pk)

    async def story_viewers(self, story_pk, amount=0):
        self.calls.append(("story_viewers", story_pk, amount))
        return [{**_user_short(1), "has_liked": True}]

    async def archive_story_days(self, amount=0, include_memories=True):
        self.calls.append(("archive_story_days", amount, include_memories))
        return [{"id": "day1", "timestamp": "2026-01-01T00:00:00+00:00", "media_count": 1, "reel_type": "archive"}]

    async def news_inbox_v1(self, mark_as_seen=False):
        self.calls.append(("news_inbox_v1", mark_as_seen))
        return {"stories": []}

    async def notification_settings(self, content_type, setting_value):
        self.calls.append(("notification_settings", content_type, setting_value))
        return True

    async def get_notes(self):
        self.calls.append(("get_notes",))
        return [_note_payload()]

    async def create_note(self, text, audience=0):
        self.calls.append(("create_note", text, audience))
        return _note_payload()

    async def delete_note(self, note_id):
        self.calls.append(("delete_note", note_id))
        return True

    async def totp_enable(self, verification_code):
        self.calls.append(("totp_enable", verification_code))
        return ["backup-code"]

    async def totp_disable(self):
        self.calls.append(("totp_disable",))
        return True

    async def challenge_resolve(self, last_json):
        self.calls.append(("challenge_resolve", last_json))
        return True


class FakeStorage:
    def __init__(self):
        self.client = FakeExpandedClient()

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
async def test_account_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        info = await ac.get("/account/info", params={"sessionid": "sid"})
        profile = await ac.patch(
            "/account/profile",
            data={"sessionid": "sid", "full_name": "New Name", "biography": "bio"},
        )
        picture = await ac.patch(
            "/account/picture",
            data={"sessionid": "sid"},
            files={"picture": ("avatar.jpg", b"image", "image/jpeg")},
        )
        private = await ac.patch("/account/privacy", data={"sessionid": "sid", "is_private": "true"})
        public = await ac.patch("/account/privacy", data={"sessionid": "sid", "is_private": "false"})

    assert info.status_code == 200 and info.json()["username"] == "account"
    assert profile.status_code == 200 and profile.json()["full_name"] == "New Name"
    assert picture.status_code == 200 and picture.json()["pk"] == "1"
    assert private.status_code == 200 and public.status_code == 200
    assert ("account_set_private",) in storage.client.calls
    assert ("account_set_public",) in storage.client.calls


@pytest.mark.asyncio
async def test_media_comment_save_pin_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        comments = await ac.get("/media/comments", params={"sessionid": "sid", "media_id": "m1", "amount": "2"})
        comment = await ac.post("/media/comment", data={"sessionid": "sid", "media_id": "m1", "text": "hello"})
        delete_comment = await ac.delete(
            "/media/comment", params={"sessionid": "sid", "media_id": "m1", "comment_pk": "10"}
        )
        replies = await ac.get(
            "/media/comment/replies",
            params={"sessionid": "sid", "media_id": "m1", "comment_id": "10", "amount": "3"},
        )
        like = await ac.post("/media/comment/like", data={"sessionid": "sid", "comment_pk": "10"})
        unlike = await ac.delete("/media/comment/like", params={"sessionid": "sid", "comment_pk": "10"})
        liked = await ac.get("/media/liked", params={"sessionid": "sid", "amount": "1", "last_media_pk": "5"})
        save = await ac.post("/media/save", data={"sessionid": "sid", "media_id": "m1", "collection_pk": "7"})
        unsave = await ac.delete(
            "/media/save", params={"sessionid": "sid", "media_id": "m1", "collection_pk": "7"}
        )
        pin = await ac.post("/media/pin", data={"sessionid": "sid", "media_pk": "1"})
        unpin = await ac.delete("/media/pin", params={"sessionid": "sid", "media_pk": "1"})

    assert comments.status_code == 200 and len(comments.json()) == 1
    assert comment.status_code == 200 and comment.json()["text"] == "hello"
    assert delete_comment.status_code == 200 and delete_comment.json() is True
    assert replies.status_code == 200 and replies.json()[0]["pk"] == "11"
    assert like.status_code == 200 and unlike.status_code == 200
    assert liked.status_code == 200 and save.status_code == 200 and unsave.status_code == 200
    assert pin.status_code == 200 and unpin.status_code == 200
    assert ("comment_bulk_delete", "m1", [10]) in storage.client.calls
    assert ("media_unsave", "m1", 7) in storage.client.calls
    assert ("media_unpin", "1") in storage.client.calls


@pytest.mark.asyncio
async def test_direct_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        inbox = await ac.get("/direct/inbox", params={"sessionid": "sid", "amount": "1"})
        thread = await ac.get("/direct/thread", params={"sessionid": "sid", "thread_id": "100", "amount": "5"})
        created = await ac.post("/direct/thread", data={"sessionid": "sid", "user_ids": ["1", "2"], "title": "Team"})
        message = await ac.post(
            "/direct/message",
            data={"sessionid": "sid", "text": "hello", "thread_ids": ["100"]},
        )
        deleted = await ac.delete(
            "/direct/message", params={"sessionid": "sid", "thread_id": "100", "message_id": "1"}
        )
        seen = await ac.patch(
            "/direct/message/seen",
            data={"sessionid": "sid", "thread_id": "100", "message_id": "1"},
        )
        empty = await ac.post(
            "/direct/message",
            data={"sessionid": "sid", "text": "hi"},
        )
        both = await ac.post(
            "/direct/message",
            data={"sessionid": "sid", "text": "hi", "user_ids": ["1"], "thread_ids": ["100"]},
        )
        single = await ac.post("/direct/thread", data={"sessionid": "sid", "user_ids": ["1"]})

    assert inbox.status_code == 200 and thread.status_code == 200
    assert created.status_code == 200 and created.json() == "100"
    assert message.status_code == 200 and message.json()["text"] == "hello"
    assert deleted.status_code == 200 and seen.status_code == 200
    assert empty.status_code == 422 and both.status_code == 422
    assert single.status_code == 422
    assert ("direct_thread_create", [1, 2], "Team") in storage.client.calls
    assert ("direct_message_seen", 100, 1) in storage.client.calls


@pytest.mark.asyncio
async def test_discovery_user_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        hashtag = await ac.get("/hashtag/info", params={"sessionid": "sid", "name": "python"})
        top = await ac.get("/hashtag/medias/top", params={"sessionid": "sid", "name": "python", "amount": "1"})
        recent = await ac.get("/hashtag/medias/recent", params={"sessionid": "sid", "name": "python", "amount": "1"})
        follow = await ac.post("/hashtag/follow", data={"sessionid": "sid", "hashtag": "python"})
        unfollow = await ac.delete("/hashtag/follow", params={"sessionid": "sid", "hashtag": "python"})
        location_by_name = await ac.get("/location/search", params={"sessionid": "sid", "name": "Berlin"})
        location_by_coords = await ac.get("/location/search", params={"sessionid": "sid", "lat": "1", "lng": "2"})
        location_missing = await ac.get("/location/search", params={"sessionid": "sid"})
        location_partial = await ac.get("/location/search", params={"sessionid": "sid", "lat": "1"})
        location = await ac.get("/location/info", params={"sessionid": "sid", "location_pk": "1"})
        location_top = await ac.get("/location/medias/top", params={"sessionid": "sid", "location_pk": "1"})
        location_recent = await ac.get("/location/medias/recent", params={"sessionid": "sid", "location_pk": "1"})
        users = await ac.get("/user/search", params={"sessionid": "sid", "query": "insta"})
        friendship = await ac.get("/user/friendship", params={"sessionid": "sid", "user_id": "1"})
        block = await ac.post("/user/block", data={"sessionid": "sid", "user_id": "1"})
        unblock = await ac.delete("/user/block", params={"sessionid": "sid", "user_id": "1"})
        requests = await ac.get("/user/follow/requests", params={"sessionid": "sid", "amount": "1"})

    for response in (
        hashtag,
        top,
        recent,
        follow,
        unfollow,
        location_by_name,
        location_by_coords,
        location,
        location_top,
        location_recent,
        users,
        friendship,
        block,
        unblock,
        requests,
    ):
        assert response.status_code == 200
    assert location_missing.status_code == 422
    assert location_partial.status_code == 422
    assert ("location_search_name", "Berlin") in storage.client.calls
    assert ("location_search", 1.0, 2.0) in storage.client.calls
    assert ("user_unblock", "1", "profile") in storage.client.calls


@pytest.mark.asyncio
async def test_highlight_story_note_notification_and_auth_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        user_highlights = await ac.get("/user/highlights", params={"sessionid": "sid", "user_id": "1"})
        highlight = await ac.get("/highlight/info", params={"sessionid": "sid", "highlight_pk": "h1"})
        created = await ac.post("/highlight", data={"sessionid": "sid", "title": "Trip", "story_ids": ["s1"]})
        edited = await ac.patch(
            "/highlight",
            data={"sessionid": "sid", "highlight_pk": "h1", "title": "Trip 2", "added_media_ids": ["s2"]},
        )
        deleted = await ac.delete("/highlight", params={"sessionid": "sid", "highlight_pk": "h1"})
        add_stories = await ac.post(
            "/highlight/stories", data={"sessionid": "sid", "highlight_pk": "h1", "story_ids": ["s1"]}
        )
        remove_stories = await ac.delete(
            "/highlight/stories", params={"sessionid": "sid", "highlight_pk": "h1", "story_ids": ["s1"]}
        )
        viewers = await ac.get("/story/viewers", params={"sessionid": "sid", "story_pk": "1"})
        archive = await ac.get("/story/archive", params={"sessionid": "sid", "include_memories": "false"})
        notifications = await ac.get("/notifications", params={"sessionid": "sid", "mark_as_seen": "true"})
        settings = await ac.get("/notifications/settings", params={"sessionid": "sid"})
        patched_settings = await ac.patch(
            "/notifications/settings",
            data={"sessionid": "sid", "content_type": "likes", "setting_value": "off"},
        )
        notes = await ac.get("/notes", params={"sessionid": "sid"})
        note = await ac.post("/note", data={"sessionid": "sid", "text": "note", "audience": "1"})
        delete_note = await ac.delete("/note", params={"sessionid": "sid", "note_id": "1"})
        totp = await ac.post("/auth/totp/enable", data={"sessionid": "sid", "verification_code": "123456"})
        disable_totp = await ac.delete("/auth/totp", params={"sessionid": "sid"})
        challenge = await ac.post(
            "/auth/challenge/resolve",
            data={"sessionid": "sid", "last_json": '{"challenge":{"api_path":"/challenge/1/nonce/"}}'},
        )
        bad_cover = await ac.patch(
            "/highlight",
            data={"sessionid": "sid", "highlight_pk": "h1", "cover": "not-json"},
        )
        bad_challenge = await ac.post(
            "/auth/challenge/resolve",
            data={"sessionid": "sid", "last_json": "not-json"},
        )
        bad_content_type = await ac.patch(
            "/notifications/settings",
            data={"sessionid": "sid", "content_type": "nope", "setting_value": "off"},
        )
        bad_setting_value = await ac.patch(
            "/notifications/settings",
            data={"sessionid": "sid", "content_type": "likes", "setting_value": "nope"},
        )

    for response in (
        user_highlights,
        highlight,
        created,
        edited,
        deleted,
        add_stories,
        remove_stories,
        viewers,
        archive,
        notifications,
        settings,
        patched_settings,
        notes,
        note,
        delete_note,
        totp,
        disable_totp,
        challenge,
    ):
        assert response.status_code == 200
    assert settings.json()["setting_values"] == ["off", "following_only", "everyone"]
    assert ("archive_story_days", 0, False) in storage.client.calls
    assert ("notification_settings", "likes", "off") in storage.client.calls
    assert ("challenge_resolve", {"challenge": {"api_path": "/challenge/1/nonce/"}}) in storage.client.calls
    assert bad_cover.status_code == 422
    assert bad_challenge.status_code == 422
    assert bad_content_type.status_code == 422
    assert bad_setting_value.status_code == 422
