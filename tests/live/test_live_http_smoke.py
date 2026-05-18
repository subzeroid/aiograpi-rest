import asyncio
import json
import os
import ssl
import urllib.parse
import urllib.request

import pytest
from aiograpi import Client

pytestmark = pytest.mark.live


def _fetch_accounts(url, count=None):
    count = count or int(os.environ.get("TEST_ACCOUNTS_COUNT", "25"))
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        url + sep + f"count={count}",
        headers={"User-Agent": "Mozilla/5.0 aiograpi-rest-http-smoke"},
    )
    with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as response:
        return json.loads(response.read())


def _request_json(base_url, method, path, *, headers=None, data=None):
    body = None
    request_headers = dict(headers or {})
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        headers=request_headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = response.read()
    return json.loads(payload)


def _assert_paginated_page(page, path):
    assert sorted(page) == ["items", "next_cursor"], f"Unexpected {path} response: {page!r}"
    assert isinstance(page["items"], list), f"Unexpected {path} items: {page!r}"
    assert isinstance(page["next_cursor"], str), f"Unexpected {path} next_cursor: {page!r}"


def _totp_code(account):
    settings = dict(account.get("client_settings") or account.get("settings") or {})
    totp_seed = settings.get("totp_seed") or account.get("totp_seed")
    if not totp_seed:
        return ""
    return Client().totp_generate_code(totp_seed)


async def _login_direct(account):
    client = Client()
    settings = dict(account.get("client_settings") or account.get("settings") or {})
    settings.pop("totp_seed", None)
    if settings:
        client.set_settings(settings)
    if account.get("proxy"):
        client.set_proxy(account["proxy"])
    kwargs = {
        "username": account["username"],
        "password": account["password"],
        "relogin": True,
    }
    verification_code = _totp_code(account)
    if verification_code:
        kwargs["verification_code"] = verification_code
    assert await client.login(**kwargs)
    return client


def _login_via_http(base_url, account):
    form = {
        "username": account["username"],
        "password": account["password"],
    }
    if account.get("proxy"):
        form["proxy"] = account["proxy"]
    verification_code = _totp_code(account)
    if verification_code:
        form["verification_code"] = verification_code

    sessionid = _request_json(base_url, "POST", "/auth/login", data=form)
    if not isinstance(sessionid, str) or not sessionid:
        raise AssertionError(f"Unexpected /auth/login response: {sessionid!r}")
    return sessionid


def _import_settings_via_http(base_url, account):
    client = asyncio.run(_login_direct(account))
    sessionid = _request_json(
        base_url,
        "PATCH",
        "/auth/settings",
        data={"settings": json.dumps(client.get_settings())},
    )
    if not isinstance(sessionid, str) or not sessionid:
        raise AssertionError(f"Unexpected /auth/settings response: {sessionid!r}")
    return sessionid


def _create_session(base_url, account):
    try:
        return _login_via_http(base_url, account)
    except Exception:
        return _import_settings_via_http(base_url, account)


def _assert_published_http_pagination(base_url, headers, public_user_id):
    for path in (
        f"/media/user/medias?user_id={public_user_id}&amount=2",
        "/hashtag/medias/top?name=instagram&amount=2",
        "/direct/inbox?thread_message_limit=1",
    ):
        _assert_paginated_page(
            _request_json(base_url, "GET", path, headers=headers),
            path,
        )


def test_live_http_login_authorize_and_user_about_flow():
    accounts_url = os.environ.get("TEST_ACCOUNTS_URL")
    if not accounts_url:
        pytest.skip("TEST_ACCOUNTS_URL not configured")

    base_url = os.environ.get("LIVE_API_BASE_URL")
    if not base_url:
        pytest.skip("LIVE_API_BASE_URL not configured")

    assert _request_json(base_url, "GET", "/health") == {"status": "ok"}

    errors = []
    for account in _fetch_accounts(accounts_url):
        try:
            sessionid = _create_session(base_url, account)
            sessionid = _request_json(
                base_url,
                "POST",
                "/auth/login/by/sessionid",
                data={"sessionid": sessionid},
            )
            headers = {"X-Session-ID": sessionid}
            user = _request_json(
                base_url,
                "GET",
                "/user/info/by/username?username=instagram",
                headers=headers,
            )
            assert user["username"] == "instagram"
            about = _request_json(
                base_url,
                "GET",
                f"/user/about?user_id={user['pk']}",
                headers=headers,
            )
            assert "is_verified" in about
            assert isinstance(about["former_usernames"], str)
            _assert_published_http_pagination(base_url, headers, user["pk"])
            return
        except Exception as exc:
            errors.append(f"{account.get('username', '?')}: {type(exc).__name__}: {exc}")

    pytest.fail("No live HTTP account succeeded: " + " | ".join(errors[:5]))
