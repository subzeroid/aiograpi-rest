#!/usr/bin/env python3
"""Minimal aiograpi-rest session flow and /user/about call."""

from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("AIOGRAPI_REST_BASE_URL", "http://localhost:8000").rstrip("/")
USER_ID = os.environ.get("AIOGRAPI_REST_USER_ID", "25025320")


def env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def post_form(path: str, fields: dict[str, str]) -> object:
    body = urlencode(fields).encode()
    request = Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def get_json(path: str, sessionid: str) -> object:
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Accept": "application/json", "X-Session-ID": sessionid},
        method="GET",
    )
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def get_sessionid() -> str:
    if sessionid := env("AIOGRAPI_REST_SESSIONID"):
        return sessionid

    if instagram_sessionid := env("AIOGRAPI_REST_INSTAGRAM_SESSIONID"):
        value = post_form("/auth/login/by/sessionid", {"sessionid": instagram_sessionid})
        if isinstance(value, str) and value:
            return value

    username = env("AIOGRAPI_REST_USERNAME")
    password = env("AIOGRAPI_REST_PASSWORD")
    if username and password:
        fields = {"username": username, "password": password}
        if verification_code := env("AIOGRAPI_REST_VERIFICATION_CODE"):
            fields["verification_code"] = verification_code
        value = post_form("/auth/login", fields)
        if isinstance(value, str) and value:
            return value

    raise SystemExit(
        "Set AIOGRAPI_REST_SESSIONID, AIOGRAPI_REST_INSTAGRAM_SESSIONID, "
        "or AIOGRAPI_REST_USERNAME/AIOGRAPI_REST_PASSWORD."
    )


def main() -> None:
    about = get_json(f"/user/about?user_id={USER_ID}", get_sessionid())
    json.dump(about, sys.stdout, indent=2, sort_keys=True)
    print()


if __name__ == "__main__":
    main()
