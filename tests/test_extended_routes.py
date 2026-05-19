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


def _direct_short_thread_payload():
    return {
        "id": "100",
        "users": [_user_short(1)],
        "named": False,
        "thread_title": "Thread",
        "pending": False,
        "thread_type": "private",
        "viewer_id": "1",
        "is_group": False,
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


def _guide_payload(guide_id="g1"):
    return {
        "id": guide_id,
        "title": "Guide",
        "description": "Guide description",
        "cover_media": _media_payload(),
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
        self.upload_paths = []

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

    async def media_comments_chunk(self, media_id, max_amount=20, min_id=None):
        self.calls.append(("media_comments_chunk", media_id, max_amount, min_id))
        return [_comment_payload()], "next-comments"

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

    async def direct_threads_chunk(self, selected_filter="", box="", thread_message_limit=None, cursor=None):
        self.calls.append(("direct_threads_chunk", selected_filter, box, thread_message_limit, cursor))
        return [_direct_thread_payload()], "next-direct"

    async def direct_thread(self, thread_id, amount=20):
        self.calls.append(("direct_thread", thread_id, amount))
        return _direct_thread_payload()

    async def direct_messages(self, thread_id, amount=20):
        self.calls.append(("direct_messages", thread_id, amount))
        return [_direct_message_payload()]

    async def direct_message(self, thread_id, message_id, amount=20):
        self.calls.append(("direct_message", thread_id, message_id, amount))
        return _direct_message_payload(str(message_id))

    async def direct_pending_chunk(self, cursor=None):
        self.calls.append(("direct_pending_chunk", cursor))
        return [_direct_thread_payload()], "next-pending"

    async def direct_requests(self, amount=20):
        self.calls.append(("direct_requests", amount))
        return [_direct_thread_payload()]

    async def direct_spam_chunk(self, cursor=None):
        self.calls.append(("direct_spam_chunk", cursor))
        return [_direct_thread_payload()], "next-spam"

    async def direct_search(self, query, mode="universal"):
        self.calls.append(("direct_search", query, mode))
        return [_user_short(2)]

    async def direct_message_search(self, query):
        self.calls.append(("direct_message_search", query))
        return [(_direct_message_payload("search1"), _direct_short_thread_payload())]

    async def direct_media(self, thread_id, amount=20):
        self.calls.append(("direct_media", thread_id, amount))
        return [_media_payload(22)]

    async def direct_active_presence(self):
        self.calls.append(("direct_active_presence",))
        return {"active": {"1": {"last_activity": 123}}}

    async def direct_users_presence(self, user_ids):
        self.calls.append(("direct_users_presence", user_ids))
        return {"users": {str(user_id): {"is_active": True} for user_id in user_ids}}

    async def direct_thread_by_participants(self, user_ids):
        self.calls.append(("direct_thread_by_participants", user_ids))
        return {"thread_id": "100", "user_ids": user_ids}

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

    async def direct_send_seen(self, thread_id):
        self.calls.append(("direct_send_seen", thread_id))
        return True

    async def direct_thread_update_title(self, thread_id, title):
        self.calls.append(("direct_thread_update_title", thread_id, title))
        return True

    async def direct_thread_mark_unread(self, thread_id):
        self.calls.append(("direct_thread_mark_unread", thread_id))
        return True

    async def direct_thread_add_users(self, thread_id, user_ids):
        self.calls.append(("direct_thread_add_users", thread_id, user_ids))
        return True

    async def direct_thread_hide(self, thread_id, move_to_spam=False):
        self.calls.append(("direct_thread_hide", thread_id, move_to_spam))
        return True

    async def direct_thread_mute(self, thread_id, revert=False):
        self.calls.append(("direct_thread_mute", thread_id, revert))
        return True

    async def direct_thread_unmute(self, thread_id):
        self.calls.append(("direct_thread_unmute", thread_id))
        return True

    async def direct_thread_mute_video_call(self, thread_id, revert=False):
        self.calls.append(("direct_thread_mute_video_call", thread_id, revert))
        return True

    async def direct_thread_unmute_video_call(self, thread_id):
        self.calls.append(("direct_thread_unmute_video_call", thread_id))
        return True

    async def direct_message_like(self, thread_id, message_id, client_context=None):
        self.calls.append(("direct_message_like", thread_id, message_id, client_context))
        return True

    async def direct_message_unlike(self, thread_id, message_id, client_context=None):
        self.calls.append(("direct_message_unlike", thread_id, message_id, client_context))
        return True

    async def direct_send_reaction(
        self,
        thread_id,
        message_id,
        emoji="❤",
        client_context=None,
        action_source="double_tap",
        target_item_type=None,
    ):
        self.calls.append(
            ("direct_send_reaction", thread_id, message_id, emoji, client_context, action_source, target_item_type)
        )
        return True

    async def direct_delete_reaction(
        self,
        thread_id,
        message_id,
        emoji="❤",
        client_context=None,
        action_source="double_tap",
        target_item_type=None,
    ):
        self.calls.append(
            ("direct_delete_reaction", thread_id, message_id, emoji, client_context, action_source, target_item_type)
        )
        return True

    async def direct_media_share(
        self,
        media_id,
        user_ids,
        send_attribute="feed_timeline",
        media_type="photo",
    ):
        self.calls.append(("direct_media_share", media_id, user_ids, send_attribute, media_type))
        return _direct_message_payload("media-share")

    async def direct_profile_share(self, user_id, user_ids=None, thread_ids=None):
        self.calls.append(("direct_profile_share", user_id, user_ids or [], thread_ids or []))
        return _direct_message_payload("profile-share")

    async def direct_story_share(self, story_id, user_ids=None, thread_ids=None):
        self.calls.append(("direct_story_share", story_id, user_ids or [], thread_ids or []))
        return _direct_message_payload("story-share")

    async def direct_send_photo(self, path, user_ids=None, thread_ids=None):
        payload = Path(path).read_bytes()
        self.upload_paths.append(Path(path))
        self.calls.append(("direct_send_photo", Path(path).suffix, payload, user_ids or [], thread_ids or []))
        return _direct_message_payload("photo-direct")

    async def direct_send_video(self, path, user_ids=None, thread_ids=None):
        payload = Path(path).read_bytes()
        self.upload_paths.append(Path(path))
        self.calls.append(("direct_send_video", Path(path).suffix, payload, user_ids or [], thread_ids or []))
        return _direct_message_payload("video-direct")

    async def direct_send_voice(self, path, user_ids=None, thread_ids=None, waveform=None):
        payload = Path(path).read_bytes()
        self.upload_paths.append(Path(path))
        self.calls.append(("direct_send_voice", Path(path).suffix, payload, user_ids or [], thread_ids or [], waveform))
        return _direct_message_payload("voice-direct")

    async def direct_send_file(self, path, user_ids=None, thread_ids=None, content_type="photo"):
        payload = Path(path).read_bytes()
        self.upload_paths.append(Path(path))
        self.calls.append(("direct_send_file", Path(path).suffix, payload, user_ids or [], thread_ids or [], content_type))
        return _direct_message_payload("file-direct")

    async def direct_pending_approve(self, thread_id):
        self.calls.append(("direct_pending_approve", thread_id))
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

    async def hashtag_medias_v1_chunk(self, name, max_amount=27, tab_key="", max_id=None):
        self.calls.append(("hashtag_medias_v1_chunk", name, max_amount, tab_key, max_id))
        return [_media_payload()], f"next-hashtag-{tab_key}"

    async def hashtag_related_hashtags(self, name):
        self.calls.append(("hashtag_related_hashtags", name))
        return [{"id": "tag-related", "name": f"{name}dev", "media_count": 2}]

    async def hashtag_medias_reels_v1(self, name, amount=27):
        self.calls.append(("hashtag_medias_reels_v1", name, amount))
        return [_media_payload(7)]

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

    async def location_medias_v1_chunk(self, location_pk, max_amount=63, tab_key="", max_id=None):
        self.calls.append(("location_medias_v1_chunk", location_pk, max_amount, tab_key, max_id))
        return [_media_payload()], f"next-location-{tab_key}"

    async def location_guides_v1(self, location_pk):
        self.calls.append(("location_guides_v1", location_pk))
        return [_guide_payload("location-guide")]

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

    async def user_follow_requests_chunk(self, max_amount=0, max_id=""):
        self.calls.append(("user_follow_requests_chunk", max_amount, max_id))
        return [_user_short(1)], "next-follow-requests"

    async def user_highlights(self, user_id, amount=0):
        self.calls.append(("user_highlights", user_id, amount))
        return [_highlight_payload()]

    async def user_pinned_medias(self, user_id):
        self.calls.append(("user_pinned_medias", user_id))
        return [_media_payload(9)]

    async def user_guides_v1(self, user_id):
        self.calls.append(("user_guides_v1", user_id))
        return [_guide_payload("user-guide")]

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

    async def story_viewers_chunk(self, story_pk, max_amount=0, max_id=""):
        self.calls.append(("story_viewers_chunk", story_pk, max_amount, max_id))
        return [{**_user_short(1), "has_liked": True}], "next-viewers"

    async def archive_story_days(self, amount=0, include_memories=True):
        self.calls.append(("archive_story_days", amount, include_memories))
        return [{"id": "day1", "timestamp": "2026-01-01T00:00:00+00:00", "media_count": 1, "reel_type": "archive"}]

    async def archive_story_days_paginated_v1(
        self,
        amount=0,
        end_cursor="",
        include_memories=True,
        reel_id="",
    ):
        self.calls.append(("archive_story_days_paginated_v1", amount, end_cursor, include_memories, reel_id))
        return [
            {"id": "day1", "timestamp": "2026-01-01T00:00:00+00:00", "media_count": 1, "reel_type": "archive"}
        ], "next-archive"

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
        info = await ac.get("/account", params={"sessionid": "sid"})
        profile = await ac.patch(
            "/account",
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
        comments = await ac.get(
            "/media/comments",
            params={"sessionid": "sid", "media_id": "m1", "amount": "2", "cursor": "comments-cursor"},
        )
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
        liked = await ac.get("/account/liked/media", params={"sessionid": "sid", "amount": "1", "last_media_pk": "5"})
        save = await ac.post("/media/save", data={"sessionid": "sid", "media_id": "m1", "collection_pk": "7"})
        unsave = await ac.delete(
            "/media/save", params={"sessionid": "sid", "media_id": "m1", "collection_pk": "7"}
        )
        pin = await ac.post("/media/pin", data={"sessionid": "sid", "media_pk": "1"})
        unpin = await ac.delete("/media/pin", params={"sessionid": "sid", "media_pk": "1"})

    assert comments.status_code == 200
    assert comments.json()["items"][0]["pk"] == "10"
    assert comments.json()["next_cursor"] == "next-comments"
    assert comment.status_code == 200 and comment.json()["text"] == "hello"
    assert delete_comment.status_code == 200 and delete_comment.json() is True
    assert replies.status_code == 200 and replies.json()[0]["pk"] == "11"
    assert like.status_code == 200 and unlike.status_code == 200
    assert liked.status_code == 200 and save.status_code == 200 and unsave.status_code == 200
    assert pin.status_code == 200 and unpin.status_code == 200
    assert ("media_comments_chunk", "m1", 2, "comments-cursor") in storage.client.calls
    assert ("comment_bulk_delete", "m1", [10]) in storage.client.calls
    assert ("media_unsave", "m1", 7) in storage.client.calls
    assert ("media_unpin", "1") in storage.client.calls


@pytest.mark.asyncio
async def test_direct_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        inbox = await ac.get("/direct/inbox", params={"sessionid": "sid", "cursor": "direct-cursor"})
        threads = await ac.get(
            "/direct/threads",
            params={
                "sessionid": "sid",
                "amount": "3",
                "selected_filter": "unread",
                "box": "primary",
                "thread_message_limit": "2",
            },
        )
        thread = await ac.get("/direct/thread", params={"sessionid": "sid", "thread_id": "100", "amount": "5"})
        messages = await ac.get("/direct/messages", params={"sessionid": "sid", "thread_id": "100", "amount": "4"})
        message_lookup = await ac.get(
            "/direct/message",
            params={"sessionid": "sid", "thread_id": "100", "message_id": "1", "amount": "6"},
        )
        pending = await ac.get("/direct/pending", params={"sessionid": "sid", "cursor": "pending-cursor"})
        requests = await ac.get("/direct/requests", params={"sessionid": "sid", "amount": "2"})
        spam = await ac.get("/direct/spam", params={"sessionid": "sid", "cursor": "spam-cursor"})
        search = await ac.get("/direct/search", params={"sessionid": "sid", "query": "user", "mode": "raven"})
        message_search = await ac.get(
            "/direct/messages/search",
            params={"sessionid": "sid", "query": "hello"},
        )
        thread_media = await ac.get("/direct/media", params={"sessionid": "sid", "thread_id": "100", "amount": "2"})
        active_presence = await ac.get("/direct/presence", params={"sessionid": "sid"})
        users_presence = await ac.get("/direct/presence", params={"sessionid": "sid", "user_ids": ["1", "2"]})
        thread_by_participants = await ac.get(
            "/direct/thread/by/participants",
            params={"sessionid": "sid", "user_ids": ["1", "2"]},
        )
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
        thread_seen = await ac.patch("/direct/thread/seen", data={"sessionid": "sid", "thread_id": "100"})
        patch_thread = await ac.patch(
            "/direct/thread",
            data={"sessionid": "sid", "thread_id": "100", "title": "Renamed", "is_unread": "true"},
        )
        add_user = await ac.post(
            "/direct/thread/user",
            data={"sessionid": "sid", "thread_id": "100", "user_ids": ["3", "4"]},
        )
        hide_thread = await ac.delete(
            "/direct/thread",
            params={"sessionid": "sid", "thread_id": "100", "move_to_spam": "true"},
        )
        mute_thread = await ac.post("/direct/thread/mute", data={"sessionid": "sid", "thread_id": "100"})
        unmute_thread = await ac.delete("/direct/thread/mute", params={"sessionid": "sid", "thread_id": "100"})
        mute_video_call = await ac.post(
            "/direct/thread/video/call/mute",
            data={"sessionid": "sid", "thread_id": "100"},
        )
        unmute_video_call = await ac.delete(
            "/direct/thread/video/call/mute",
            params={"sessionid": "sid", "thread_id": "100"},
        )
        like_message = await ac.post(
            "/direct/message/like",
            data={"sessionid": "sid", "thread_id": "100", "message_id": "1", "client_context": "ctx"},
        )
        unlike_message = await ac.delete(
            "/direct/message/like",
            params={"sessionid": "sid", "thread_id": "100", "message_id": "1", "client_context": "ctx"},
        )
        react_message = await ac.post(
            "/direct/message/reaction",
            data={
                "sessionid": "sid",
                "thread_id": "100",
                "message_id": "1",
                "emoji": "\U0001f525",
                "client_context": "ctx",
                "action_source": "long_press",
                "target_item_type": "text",
            },
        )
        delete_reaction = await ac.delete(
            "/direct/message/reaction",
            params={
                "sessionid": "sid",
                "thread_id": "100",
                "message_id": "1",
                "emoji": "\U0001f525",
                "client_context": "ctx",
                "action_source": "long_press",
                "target_item_type": "text",
            },
        )
        share_media = await ac.post(
            "/direct/media",
            data={
                "sessionid": "sid",
                "media_id": "m1",
                "user_ids": ["1", "2"],
                "send_attribute": "feed_short_url",
                "media_type": "video",
            },
        )
        share_profile = await ac.post(
            "/direct/profile",
            data={"sessionid": "sid", "user_id": "1", "user_ids": ["2"]},
        )
        share_story = await ac.post(
            "/direct/story",
            data={"sessionid": "sid", "story_id": "story1", "thread_ids": ["100"]},
        )
        send_photo = await ac.post(
            "/direct/photo",
            data={"sessionid": "sid", "user_ids": ["2"]},
            files={"file": ("photo.jpg", b"photo-bytes", "image/jpeg")},
        )
        send_video = await ac.post(
            "/direct/video",
            data={"sessionid": "sid", "thread_ids": ["100"]},
            files={"file": ("video.mp4", b"video-bytes", "video/mp4")},
        )
        send_voice = await ac.post(
            "/direct/voice",
            data={"sessionid": "sid", "thread_ids": ["100"], "waveform": ["0.1", "0.2"]},
            files={"file": ("voice.m4a", b"voice-bytes", "audio/mp4")},
        )
        send_file = await ac.post(
            "/direct/file",
            data={"sessionid": "sid", "user_ids": ["2"], "content_type": "video"},
            files={"file": ("document.bin", b"file-bytes", "application/octet-stream")},
        )
        approve_pending = await ac.patch(
            "/direct/pending",
            data={"sessionid": "sid", "thread_id": "100", "approved": "true"},
        )
        invalid_patch_thread = await ac.patch("/direct/thread", data={"sessionid": "sid", "thread_id": "100"})
        invalid_thread_read_state = await ac.patch(
            "/direct/thread",
            data={"sessionid": "sid", "thread_id": "100", "is_unread": "false"},
        )
        invalid_profile_share = await ac.post("/direct/profile", data={"sessionid": "sid", "user_id": "1"})
        invalid_direct_file_targets = await ac.post(
            "/direct/file",
            data={"sessionid": "sid", "user_ids": ["2"], "thread_ids": ["100"]},
            files={"file": ("document.bin", b"file-bytes", "application/octet-stream")},
        )
        invalid_pending = await ac.patch(
            "/direct/pending",
            data={"sessionid": "sid", "thread_id": "100", "approved": "false"},
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

    assert inbox.status_code == 200 and threads.status_code == 200 and thread.status_code == 200
    assert messages.status_code == 200 and message_lookup.status_code == 200
    assert pending.status_code == 200 and requests.status_code == 200 and spam.status_code == 200
    assert search.status_code == 200 and message_search.status_code == 200
    assert thread_media.status_code == 200 and active_presence.status_code == 200
    assert users_presence.status_code == 200 and thread_by_participants.status_code == 200
    assert threads.json()[0]["id"] == "100"
    assert messages.json()[0]["text"] == "hello"
    assert message_lookup.json()["id"] == "1"
    assert pending.json()["next_cursor"] == "next-pending"
    assert spam.json()["next_cursor"] == "next-spam"
    assert search.json()[0]["username"] == "user2"
    assert message_search.json()[0]["message"]["id"] == "search1"
    assert message_search.json()[0]["thread"]["id"] == "100"
    assert thread_media.json()[0]["pk"] == 22
    assert active_presence.json()["active"]["1"]["last_activity"] == 123
    assert users_presence.json()["users"]["2"]["is_active"] is True
    assert thread_by_participants.json()["thread_id"] == "100"
    assert created.status_code == 200 and created.json() == "100"
    assert message.status_code == 200 and message.json()["text"] == "hello"
    assert deleted.status_code == 200 and seen.status_code == 200 and thread_seen.status_code == 200
    assert patch_thread.status_code == 200 and add_user.status_code == 200 and hide_thread.status_code == 200
    assert mute_thread.status_code == 200 and unmute_thread.status_code == 200
    assert mute_video_call.status_code == 200 and unmute_video_call.status_code == 200
    assert like_message.status_code == 200 and unlike_message.status_code == 200
    assert react_message.status_code == 200 and delete_reaction.status_code == 200
    assert share_media.status_code == 200 and share_media.json()["id"] == "media-share"
    assert share_profile.status_code == 200 and share_profile.json()["id"] == "profile-share"
    assert share_story.status_code == 200 and share_story.json()["id"] == "story-share"
    assert send_photo.status_code == 200 and send_photo.json()["id"] == "photo-direct"
    assert send_video.status_code == 200 and send_video.json()["id"] == "video-direct"
    assert send_voice.status_code == 200 and send_voice.json()["id"] == "voice-direct"
    assert send_file.status_code == 200 and send_file.json()["id"] == "file-direct"
    assert approve_pending.status_code == 200
    assert invalid_patch_thread.status_code == 422
    assert invalid_thread_read_state.status_code == 422
    assert invalid_profile_share.status_code == 422
    assert invalid_direct_file_targets.status_code == 422
    assert invalid_pending.status_code == 422
    assert empty.status_code == 422 and both.status_code == 422
    assert single.status_code == 422
    assert inbox.json()["next_cursor"] == "next-direct"
    assert ("direct_threads_chunk", "", "", None, "direct-cursor") in storage.client.calls
    assert ("direct_threads", 3, "unread", "primary", 2) in storage.client.calls
    assert ("direct_messages", 100, 4) in storage.client.calls
    assert ("direct_message", 100, 1, 6) in storage.client.calls
    assert ("direct_pending_chunk", "pending-cursor") in storage.client.calls
    assert ("direct_requests", 2) in storage.client.calls
    assert ("direct_spam_chunk", "spam-cursor") in storage.client.calls
    assert ("direct_search", "user", "raven") in storage.client.calls
    assert ("direct_message_search", "hello") in storage.client.calls
    assert ("direct_media", 100, 2) in storage.client.calls
    assert ("direct_active_presence",) in storage.client.calls
    assert ("direct_users_presence", [1, 2]) in storage.client.calls
    assert ("direct_thread_by_participants", [1, 2]) in storage.client.calls
    assert ("direct_thread_create", [1, 2], "Team") in storage.client.calls
    assert ("direct_message_seen", 100, 1) in storage.client.calls
    assert ("direct_send_seen", 100) in storage.client.calls
    assert ("direct_thread_update_title", 100, "Renamed") in storage.client.calls
    assert ("direct_thread_mark_unread", 100) in storage.client.calls
    assert ("direct_thread_add_users", 100, [3, 4]) in storage.client.calls
    assert ("direct_thread_hide", 100, True) in storage.client.calls
    assert ("direct_thread_mute", 100, False) in storage.client.calls
    assert ("direct_thread_unmute", 100) in storage.client.calls
    assert ("direct_thread_mute_video_call", 100, False) in storage.client.calls
    assert ("direct_thread_unmute_video_call", 100) in storage.client.calls
    assert ("direct_message_like", 100, 1, "ctx") in storage.client.calls
    assert ("direct_message_unlike", 100, 1, "ctx") in storage.client.calls
    assert ("direct_send_reaction", 100, 1, "\U0001f525", "ctx", "long_press", "text") in storage.client.calls
    assert ("direct_delete_reaction", 100, 1, "\U0001f525", "ctx", "long_press", "text") in storage.client.calls
    assert ("direct_media_share", "m1", [1, 2], "feed_short_url", "video") in storage.client.calls
    assert ("direct_profile_share", "1", [2], []) in storage.client.calls
    assert ("direct_story_share", "story1", [], [100]) in storage.client.calls
    assert ("direct_send_photo", ".jpg", b"photo-bytes", [2], []) in storage.client.calls
    assert ("direct_send_video", ".mp4", b"video-bytes", [], [100]) in storage.client.calls
    assert ("direct_send_voice", ".m4a", b"voice-bytes", [], [100], [0.1, 0.2]) in storage.client.calls
    assert ("direct_send_file", ".bin", b"file-bytes", [2], [], "video") in storage.client.calls
    assert storage.client.upload_paths
    assert all(not path.exists() for path in storage.client.upload_paths)
    assert ("direct_pending_approve", 100) in storage.client.calls


@pytest.mark.asyncio
async def test_discovery_user_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        hashtag = await ac.get("/hashtag", params={"sessionid": "sid", "name": "python"})
        top = await ac.get("/hashtag/media/top", params={"sessionid": "sid", "name": "python", "amount": "1"})
        recent = await ac.get("/hashtag/media/recent", params={"sessionid": "sid", "name": "python", "amount": "1"})
        related = await ac.get("/hashtag/related", params={"sessionid": "sid", "name": "python"})
        reels = await ac.get("/hashtag/reels", params={"sessionid": "sid", "name": "python", "amount": "2"})
        follow = await ac.post("/hashtag/follow", data={"sessionid": "sid", "hashtag": "python"})
        unfollow = await ac.delete("/hashtag/follow", params={"sessionid": "sid", "hashtag": "python"})
        location_by_name = await ac.get("/search/locations", params={"sessionid": "sid", "name": "Berlin"})
        location_by_coords = await ac.get("/search/locations", params={"sessionid": "sid", "lat": "1", "lng": "2"})
        location_missing = await ac.get("/search/locations", params={"sessionid": "sid"})
        location_partial = await ac.get("/search/locations", params={"sessionid": "sid", "lat": "1"})
        location = await ac.get("/location", params={"sessionid": "sid", "location_pk": "1"})
        location_top = await ac.get("/location/media/top", params={"sessionid": "sid", "location_pk": "1"})
        location_recent = await ac.get("/location/media/recent", params={"sessionid": "sid", "location_pk": "1"})
        location_guides = await ac.get("/location/guides", params={"sessionid": "sid", "location_pk": "1"})
        users = await ac.get("/search/users", params={"sessionid": "sid", "query": "insta"})
        friendship = await ac.get("/user/friendship", params={"sessionid": "sid", "user_id": "1"})
        block = await ac.post("/user/block", data={"sessionid": "sid", "user_id": "1"})
        unblock = await ac.delete("/user/block", params={"sessionid": "sid", "user_id": "1"})
        user_pinned = await ac.get("/user/pinned/posts", params={"sessionid": "sid", "user_id": "1"})
        user_guides = await ac.get("/user/guides", params={"sessionid": "sid", "user_id": "1"})
        requests = await ac.get("/account/follow/requests", params={"sessionid": "sid", "amount": "1"})

    for response in (
        hashtag,
        top,
        recent,
        related,
        reels,
        follow,
        unfollow,
        location_by_name,
        location_by_coords,
        location,
        location_top,
        location_recent,
        location_guides,
        users,
        friendship,
        block,
        unblock,
        user_pinned,
        user_guides,
        requests,
    ):
        assert response.status_code == 200
    assert location_missing.status_code == 422
    assert location_partial.status_code == 422
    assert ("location_search_name", "Berlin") in storage.client.calls
    assert ("location_search", 1.0, 2.0) in storage.client.calls
    assert ("hashtag_related_hashtags", "python") in storage.client.calls
    assert ("hashtag_medias_reels_v1", "python", 2) in storage.client.calls
    assert ("location_guides_v1", 1) in storage.client.calls
    assert ("user_unblock", "1", "profile") in storage.client.calls
    assert ("user_pinned_medias", 1) in storage.client.calls
    assert ("user_guides_v1", 1) in storage.client.calls


@pytest.mark.asyncio
async def test_highlight_story_note_notification_and_auth_routes(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        user_highlights = await ac.get("/user/highlights", params={"sessionid": "sid", "user_id": "1"})
        highlight = await ac.get("/highlight", params={"sessionid": "sid", "highlight_pk": "h1"})
        created = await ac.post("/highlight", data={"sessionid": "sid", "title": "Trip", "story_ids": ["s1"]})
        edited = await ac.patch(
            "/highlight",
            data={"sessionid": "sid", "highlight_pk": "h1", "title": "Trip 2", "added_media_ids": ["s2"]},
        )
        deleted = await ac.delete("/highlight", params={"sessionid": "sid", "highlight_pk": "h1"})
        add_stories = await ac.post(
            "/highlight/story", data={"sessionid": "sid", "highlight_pk": "h1", "story_ids": ["s1"]}
        )
        remove_stories = await ac.delete(
            "/highlight/story", params={"sessionid": "sid", "highlight_pk": "h1", "story_ids": ["s1"]}
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
        totp = await ac.post("/auth/totp", data={"sessionid": "sid", "verification_code": "123456"})
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
    assert viewers.json()["next_cursor"] == "next-viewers"
    assert archive.json()["next_cursor"] == "next-archive"
    assert ("archive_story_days_paginated_v1", 50, "", False, "") in storage.client.calls
    assert ("notification_settings", "likes", "off") in storage.client.calls
    assert ("challenge_resolve", {"challenge": {"api_path": "/challenge/1/nonce/"}}) in storage.client.calls
    assert bad_cover.status_code == 422
    assert bad_challenge.status_code == 422
    assert bad_content_type.status_code == 422
    assert bad_setting_value.status_code == 422


@pytest.mark.asyncio
async def test_story_viewers_returns_empty_page_when_instagram_omits_viewers(storage):
    async def no_viewers(story_pk, max_amount=0, max_id=""):
        storage.client.calls.append(("story_viewers_chunk", story_pk, max_amount, max_id))
        raise KeyError("viewers")

    storage.client.story_viewers_chunk = no_viewers

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/story/viewers", params={"sessionid": "sid", "story_pk": "1"})

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": ""}
    assert ("story_viewers_chunk", "1", 50, "") in storage.client.calls


@pytest.mark.asyncio
async def test_story_viewers_keeps_unexpected_key_errors_visible(storage):
    async def missing_other_key(story_pk, max_amount=0, max_id=""):
        raise KeyError("unexpected")

    storage.client.story_viewers_chunk = missing_other_key

    with pytest.raises(KeyError, match="unexpected"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.get("/story/viewers", params={"sessionid": "sid", "story_pk": "1"})
