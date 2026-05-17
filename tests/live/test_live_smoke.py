import asyncio
import json
import os
import ssl
import urllib.request
from contextlib import asynccontextmanager

import pytest
from aiograpi import Client
from httpx import ASGITransport, AsyncClient

from dependencies import get_clients
from main import app
from storages import ClientStorage

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
