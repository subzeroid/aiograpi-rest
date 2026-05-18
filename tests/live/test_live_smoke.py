import asyncio
import json
import os
import ssl
import urllib.request
from contextlib import asynccontextmanager
from io import BytesIO

import pytest
from aiograpi import Client
from httpx import ASGITransport, AsyncClient
from PIL import Image

from aiograpi_rest.dependencies import get_clients
from aiograpi_rest.main import app
from aiograpi_rest.storages import ClientStorage

pytestmark = pytest.mark.live


def fetch_accounts(url, count=None):
    count = count or int(os.environ.get("TEST_ACCOUNTS_COUNT", "25"))
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        url + sep + f"count={count}",
        headers={"User-Agent": "Mozilla/5.0 aiograpi-rest-aiograpi-smoke"},
    )
    with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as response:
        return json.loads(response.read())


@asynccontextmanager
async def rest_api_for_account(account, tmp_path):
    def client_factory():
        rest_client = Client()
        if account.get("proxy"):
            rest_client.set_proxy(account["proxy"])
        return rest_client

    storage = ClientStorage(db_path=str(tmp_path / "db.json"), client_factory=client_factory)
    app.dependency_overrides[get_clients] = lambda: storage
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
            yield api
    finally:
        app.dependency_overrides.clear()
        storage.close()


async def try_settings_import_user_about(account, tmp_path):
    settings = dict(account.get("client_settings") or account.get("settings") or {})
    settings.pop("totp_seed", None)
    if not settings:
        raise AssertionError("account has no client settings")

    async with rest_api_for_account(account, tmp_path) as api:
        settings_response = await api.patch(
            "/auth/settings",
            data={"settings": json.dumps(settings)},
        )
        assert settings_response.status_code == 200, settings_response.text
        sessionid = settings_response.json()

        rest_user_response = await api.get(
            "/user/info/by/username",
            params={"username": "instagram"},
            headers={"X-Session-ID": sessionid},
        )
        assert rest_user_response.status_code == 200, rest_user_response.text
        rest_user = rest_user_response.json()
        assert rest_user["username"] == "instagram"

        rest_about_response = await api.get(
            "/user/about",
            params={"user_id": rest_user["pk"]},
            headers={"X-Session-ID": sessionid},
        )
        assert rest_about_response.status_code == 200, rest_about_response.text
        rest_about = rest_about_response.json()
        assert "is_verified" in rest_about
        assert isinstance(rest_about["former_usernames"], str)


def _story_jpeg_bytes():
    image = Image.new("RGB", (720, 1280), (33, 92, 162))
    output = BytesIO()
    image.save(output, format="JPEG", quality=90)
    return output.getvalue()


def _assert_downloaded_image(content):
    assert len(content) > 1024
    image = Image.open(BytesIO(content))
    assert image.width > 0
    assert image.height > 0
    image.verify()


def _assert_paginated_page(response):
    assert response.status_code == 200, response.text
    page = response.json()
    assert sorted(page) == ["items", "next_cursor"]
    assert isinstance(page["items"], list)
    assert isinstance(page["next_cursor"], str)
    return page


def _first_location_pk(*pages):
    for page in pages:
        for item in page["items"]:
            location = item.get("location") if isinstance(item, dict) else None
            if isinstance(location, dict) and location.get("pk"):
                return location["pk"]
    return os.environ.get("LIVE_LOCATION_PK", "")


async def _import_session_from_account_settings(api, account):
    settings = dict(account.get("client_settings") or account.get("settings") or {})
    settings.pop("totp_seed", None)
    if not settings:
        raise AssertionError("account has no client settings")

    settings_response = await api.patch(
        "/auth/settings",
        data={"settings": json.dumps(settings)},
    )
    assert settings_response.status_code == 200, settings_response.text
    return settings_response.json()


async def _wait_for_story(api, headers, user_id, story_pk):
    for _ in range(12):
        stories_response = await api.get(
            "/story/user/stories",
            params={"user_id": user_id},
            headers=headers,
        )
        assert stories_response.status_code == 200, stories_response.text
        stories = stories_response.json()
        for story in stories:
            if str(story["pk"]) == str(story_pk):
                return story
        await asyncio.sleep(5)
    raise AssertionError(f"Uploaded story {story_pk} was not found in /story/user/stories")


async def try_settings_import_paginated_read_lists(account, tmp_path):
    async with rest_api_for_account(account, tmp_path) as api:
        sessionid = await _import_session_from_account_settings(api, account)
        headers = {"X-Session-ID": sessionid}

        account_response = await api.get("/account/info", headers=headers)
        assert account_response.status_code == 200, account_response.text
        account_user_id = account_response.json()["pk"]

        public_user_response = await api.get(
            "/user/info/by/username",
            params={"username": "instagram"},
            headers=headers,
        )
        assert public_user_response.status_code == 200, public_user_response.text
        public_user_id = public_user_response.json()["pk"]

        media_page = _assert_paginated_page(
            await api.get(
                "/user/medias",
                params={"user_id": public_user_id, "amount": 2},
                headers=headers,
            )
        )
        hashtag_top_page = _assert_paginated_page(
            await api.get(
                "/hashtag/medias/top",
                params={"name": "instagram", "amount": 2},
                headers=headers,
            )
        )
        hashtag_recent_page = _assert_paginated_page(
            await api.get(
                "/hashtag/medias/recent",
                params={"name": "instagram", "amount": 2},
                headers=headers,
            )
        )

        for path, params in (
            ("/user/clips", {"user_id": public_user_id, "amount": 2}),
            ("/user/videos", {"user_id": public_user_id, "amount": 2}),
            ("/user/followers", {"user_id": account_user_id, "amount": 2}),
            ("/user/following", {"user_id": account_user_id, "amount": 2}),
            ("/user/follow/requests", {"amount": 2}),
            ("/direct/inbox", {"thread_message_limit": 1}),
            ("/story/archive", {"amount": 2, "include_memories": False}),
        ):
            _assert_paginated_page(await api.get(path, params=params, headers=headers))

        location_pk = _first_location_pk(media_page, hashtag_top_page, hashtag_recent_page)
        if location_pk:
            for path in ("/location/medias/top", "/location/medias/recent"):
                _assert_paginated_page(
                    await api.get(
                        path,
                        params={"location_pk": location_pk, "amount": 2},
                        headers=headers,
                    )
                )


async def try_settings_import_story_upload_image(account, tmp_path):
    async with rest_api_for_account(account, tmp_path) as api:
        sessionid = await _import_session_from_account_settings(api, account)
        headers = {"X-Session-ID": sessionid}

        account_response = await api.get("/account/info", headers=headers)
        assert account_response.status_code == 200, account_response.text
        user_id = account_response.json()["pk"]

        upload_response = await api.post(
            "/story/upload",
            data={"caption": "aiograpi-rest live story smoke"},
            files={"file": ("aiograpi-rest-live.jpg", BytesIO(_story_jpeg_bytes()), "image/jpeg")},
            headers=headers,
        )
        assert upload_response.status_code == 200, upload_response.text
        uploaded_story = upload_response.json()
        story_pk = uploaded_story["pk"]
        assert uploaded_story["id"]
        assert uploaded_story["media_type"] == 1

        try:
            story_info_response = await api.get(
                "/story/info",
                params={"story_pk": story_pk},
                headers=headers,
            )
            assert story_info_response.status_code == 200, story_info_response.text
            assert str(story_info_response.json()["pk"]) == str(story_pk)

            listed_story = await _wait_for_story(api, headers, user_id, story_pk)
            assert str(listed_story["pk"]) == str(story_pk)

            viewers_response = await api.get(
                "/story/viewers",
                params={"story_pk": story_pk, "amount": 2},
                headers=headers,
            )
            _assert_paginated_page(viewers_response)

            download_response = await api.get(
                "/story/download",
                params={"story_pk": story_pk},
                headers=headers,
            )
            assert download_response.status_code == 200, download_response.text
            _assert_downloaded_image(download_response.content)
        finally:
            delete_response = await api.delete(
                "/story",
                params={"story_pk": story_pk},
                headers=headers,
            )
            assert delete_response.status_code in {200, 404}, delete_response.text


@pytest.mark.asyncio
async def test_live_settings_import_user_about_and_rest_header_session(tmp_path):
    url = os.environ.get("TEST_ACCOUNTS_URL")
    if not url:
        pytest.skip("TEST_ACCOUNTS_URL not configured")

    accounts = fetch_accounts(url)
    timeout = int(os.environ.get("LIVE_ACCOUNT_TIMEOUT", "90"))
    errors = []
    for account in accounts:
        try:
            await asyncio.wait_for(try_settings_import_user_about(account, tmp_path), timeout=timeout)
            return
        except Exception as exc:
            errors.append(f"{account.get('username', '?')}: {type(exc).__name__}: {exc}")

    pytest.fail("No live test account succeeded: " + " | ".join(errors[:5]))


@pytest.mark.asyncio
async def test_live_paginated_read_lists_return_items_and_next_cursor(tmp_path):
    url = os.environ.get("TEST_ACCOUNTS_URL")
    if not url:
        pytest.skip("TEST_ACCOUNTS_URL not configured")

    count = int(os.environ.get("LIVE_PAGINATION_ACCOUNTS_COUNT", "5"))
    accounts = fetch_accounts(url, count=count)
    timeout = int(os.environ.get("LIVE_PAGINATION_TIMEOUT", "180"))
    errors = []
    for account in accounts:
        try:
            await asyncio.wait_for(try_settings_import_paginated_read_lists(account, tmp_path), timeout=timeout)
            return
        except Exception as exc:
            errors.append(f"{account.get('username', '?')}: {type(exc).__name__}: {exc}")

    pytest.fail("No live pagination account succeeded: " + " | ".join(errors[:5]))


@pytest.mark.asyncio
async def test_live_story_upload_creates_visible_downloadable_image_story(tmp_path):
    url = os.environ.get("TEST_ACCOUNTS_URL")
    if not url:
        pytest.skip("TEST_ACCOUNTS_URL not configured")

    count = int(os.environ.get("LIVE_STORY_ACCOUNTS_COUNT", "5"))
    accounts = fetch_accounts(url, count=count)
    timeout = int(os.environ.get("LIVE_STORY_TIMEOUT", "240"))
    errors = []
    for account in accounts:
        try:
            await asyncio.wait_for(try_settings_import_story_upload_image(account, tmp_path), timeout=timeout)
            return
        except Exception as exc:
            errors.append(f"{account.get('username', '?')}: {type(exc).__name__}: {exc}")

    pytest.fail("No live story upload account succeeded: " + " | ".join(errors[:5]))
