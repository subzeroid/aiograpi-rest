import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

import main
from main import app

ROOT = Path(__file__).resolve().parents[1]


def project_version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]


@pytest.mark.asyncio
async def test_root_redirects_to_docs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/", follow_redirects=False)
    assert response.status_code in {307, 308}
    assert response.headers["location"] == "/docs"


@pytest.mark.asyncio
async def test_deps_reports_runtime_dependencies():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/deps")
    assert response.status_code == 200
    data = response.json()
    assert {"aiograpi", "fastapi", "pydantic", "uvicorn"} <= set(data)
    assert data["aiograpi"]
    assert len(data) > 1


@pytest.mark.asyncio
async def test_health_reports_liveness():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_checks_storage_and_dependencies():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["storage"]["status"] == "ok"
    assert data["checks"]["dependencies"]["status"] == "ok"
    assert data["checks"]["dependencies"]["missing"] == []


@pytest.mark.asyncio
async def test_ready_returns_503_when_dependency_is_missing(monkeypatch):
    def fake_version(name):
        if name == "aiograpi":
            raise PackageNotFoundError(name)
        return "test-version"

    monkeypatch.setattr(main, "package_version", fake_version)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["checks"]["dependencies"]["status"] == "error"
    assert data["checks"]["dependencies"]["missing"] == ["aiograpi"]


@pytest.mark.asyncio
async def test_ready_returns_503_when_storage_fails(monkeypatch):
    class BrokenStorage:
        def __init__(self):
            raise RuntimeError("storage unavailable")

    monkeypatch.setattr(main, "ClientStorage", BrokenStorage)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert data["checks"]["storage"]["status"] == "error"
    assert data["checks"]["storage"]["detail"] == "storage unavailable"


@pytest.mark.asyncio
async def test_metrics_exports_prometheus_text():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "# HELP aiograpi_rest_info Service build information." in body
    assert f'aiograpi_rest_info{{version="{project_version()}"' in body
    assert "aiograpi_rest_uptime_seconds " in body
    assert 'aiograpi_rest_dependency_info{name="aiograpi"' in body


@pytest.mark.asyncio
async def test_build_reports_runtime_metadata(monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc123")
    monkeypatch.setenv("BUILD_TIME", "2026-05-16T00:00:00Z")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/build")
    assert response.status_code == 200
    assert response.json() == {
        "name": "aiograpi-rest",
        "version": project_version(),
        "python_version": main.platform.python_version(),
        "git_sha": "abc123",
        "build_time": "2026-05-16T00:00:00Z",
    }


def test_git_sha_returns_none_when_env_and_git_are_unavailable(monkeypatch):
    monkeypatch.delenv("GIT_SHA", raising=False)
    monkeypatch.delenv("COMMIT_SHA", raising=False)
    monkeypatch.delenv("SOURCE_VERSION", raising=False)

    def broken_run(*args, **kwargs):
        raise OSError("git unavailable")

    monkeypatch.setattr(main.subprocess, "run", broken_run)
    assert main._git_sha() is None


def test_git_sha_returns_git_short_sha(monkeypatch):
    monkeypatch.delenv("GIT_SHA", raising=False)
    monkeypatch.delenv("COMMIT_SHA", raising=False)
    monkeypatch.delenv("SOURCE_VERSION", raising=False)

    class Completed:
        stdout = "abc123\n"

    monkeypatch.setattr(main.subprocess, "run", lambda *args, **kwargs: Completed())
    assert main._git_sha() == "abc123"


@pytest.mark.asyncio
async def test_version_stays_as_hidden_deps_alias():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        deps_response = await ac.get("/deps")
        version_response = await ac.get("/version")
    assert version_response.status_code == 200
    assert version_response.json() == deps_response.json()


@pytest.mark.asyncio
async def test_openapi_contains_user_about():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")
    assert response.status_code == 200
    methods = response.json()["paths"]["/user/about"]
    assert "get" in methods
    assert "post" not in methods


@pytest.mark.asyncio
async def test_openapi_reports_app_version_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "aiograpi-rest"
    assert data["info"]["version"] == project_version()
    assert "[GitHub subzeroid/aiograpi-rest]" in data["info"]["description"]
    assert "GitHub repository" not in data["info"]["description"]
    assert "https://github.com/subzeroid/aiograpi-rest" in data["info"]["description"]
    assert "https://hikerapi.com/p/7RAo9ACK" in data["info"]["description"]
    assert "HikerAPI with 100 free requests" in data["info"]["description"]
    assert "promo code" not in data["info"]["description"]
    assert "`7RAo9ACK`" not in data["info"]["description"]
    assert "externalDocs" not in data


@pytest.mark.asyncio
async def test_openapi_uses_sessionid_authorize_button_for_protected_routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["components"]["securitySchemes"]["SessionId"] == {
        "type": "apiKey",
        "description": "Paste a saved aiograpi-rest sessionid. Get one from `POST /auth/login` or `POST /auth/login/by/sessionid`.",
        "in": "header",
        "name": "X-Session-ID",
    }

    public_paths = {
        "/auth/login",
        "/auth/login/by/sessionid",
        "/health",
        "/ready",
        "/metrics",
        "/build",
        "/deps",
        "/media/id",
        "/media/pk",
        "/media/pk/from/code",
        "/media/pk/from/url",
        "/story/pk/from/url",
    }
    for path, methods in schema["paths"].items():
        for operation in methods.values():
            parameters = operation.get("parameters", [])
            assert not [
                parameter for parameter in parameters if parameter.get("name") == "sessionid"
            ], path
            if path in public_paths:
                assert "security" not in operation
            else:
                assert operation["security"] == [{"SessionId": []}], path


@pytest.mark.asyncio
async def test_openapi_uses_rest_http_methods():
    expected_methods = {
        "/account/info": {"get"},
        "/account/picture": {"patch"},
        "/account/privacy": {"patch"},
        "/account/profile": {"patch"},
        "/album/download": {"get"},
        "/album/download/by/urls": {"get"},
        "/album/upload": {"post"},
        "/auth/challenge/resolve": {"post"},
        "/auth/login": {"post"},
        "/auth/login/by/sessionid": {"post"},
        "/auth/relogin": {"patch"},
        "/auth/settings": {"get", "patch"},
        "/auth/timeline/feed": {"get"},
        "/auth/totp": {"delete"},
        "/auth/totp/enable": {"post"},
        "/build": {"get"},
        "/clip/download": {"get"},
        "/clip/download/by/url": {"get"},
        "/clip/upload": {"post"},
        "/clip/upload/by/url": {"post"},
        "/deps": {"get"},
        "/direct/inbox": {"get"},
        "/direct/message": {"delete", "post"},
        "/direct/message/seen": {"patch"},
        "/direct/thread": {"get", "post"},
        "/hashtag/follow": {"delete", "post"},
        "/hashtag/info": {"get"},
        "/hashtag/medias/recent": {"get"},
        "/hashtag/medias/top": {"get"},
        "/highlight": {"delete", "patch", "post"},
        "/highlight/info": {"get"},
        "/highlight/stories": {"delete", "post"},
        "/health": {"get"},
        "/igtv/download": {"get"},
        "/igtv/download/by/url": {"get"},
        "/igtv/upload": {"post"},
        "/igtv/upload/by/url": {"post"},
        "/insights/account": {"get"},
        "/insights/media": {"get"},
        "/insights/media/feed/all": {"get"},
        "/location/info": {"get"},
        "/location/medias/recent": {"get"},
        "/location/medias/top": {"get"},
        "/location/search": {"get"},
        "/metrics": {"get"},
        "/media": {"delete", "patch"},
        "/media/archive": {"delete", "post"},
        "/media/comment": {"delete", "post"},
        "/media/comment/like": {"delete", "post"},
        "/media/comment/replies": {"get"},
        "/media/comments": {"get"},
        "/media/id": {"get"},
        "/media/info": {"get"},
        "/media/like": {"delete", "post"},
        "/media/liked": {"get"},
        "/media/likers": {"get"},
        "/media/oembed": {"get"},
        "/media/pin": {"delete", "post"},
        "/media/pk": {"get"},
        "/media/pk/from/code": {"get"},
        "/media/pk/from/url": {"get"},
        "/media/save": {"delete", "post"},
        "/media/seen": {"patch"},
        "/media/user": {"get"},
        "/media/user/medias": {"get"},
        "/media/usertag/medias": {"get"},
        "/note": {"delete", "post"},
        "/notes": {"get"},
        "/notifications": {"get"},
        "/notifications/settings": {"get", "patch"},
        "/photo/download": {"get"},
        "/photo/download/by/url": {"get"},
        "/photo/upload": {"post"},
        "/photo/upload/by/url": {"post"},
        "/ready": {"get"},
        "/story": {"delete"},
        "/story/archive": {"get"},
        "/story/download": {"get"},
        "/story/download/by/url": {"get"},
        "/story/info": {"get"},
        "/story/like": {"delete", "post"},
        "/story/pk/from/url": {"get"},
        "/story/seen": {"patch"},
        "/story/upload": {"post"},
        "/story/upload/by/url": {"post"},
        "/story/user/stories": {"get"},
        "/story/viewers": {"get"},
        "/user/about": {"get"},
        "/user/block": {"delete", "post"},
        "/user/follow/requests": {"get"},
        "/user/followers": {"get"},
        "/user/following": {"get"},
        "/user/friendship": {"get"},
        "/user/highlights": {"get"},
        "/user/id/from/username": {"get"},
        "/user/info": {"get"},
        "/user/info/by/username": {"get"},
        "/user/mute/posts": {"delete", "post"},
        "/user/mute/stories": {"delete", "post"},
        "/user/follower": {"delete"},
        "/user/follow": {"delete", "post"},
        "/user/search": {"get"},
        "/user/username/from/id": {"get"},
        "/video/download": {"get"},
        "/video/download/by/url": {"get"},
        "/video/upload": {"post"},
        "/video/upload/by/url": {"post"},
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert set(paths) == set(expected_methods)
    for path, methods in expected_methods.items():
        assert set(paths[path]) == methods


@pytest.mark.asyncio
async def test_openapi_removes_undo_style_paths():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert not {
        "/media/delete",
        "/media/edit",
        "/media/unarchive",
        "/media/unlike",
        "/story/delete",
        "/story/unlike",
        "/user/remove/follower",
        "/user/unfollow",
        "/user/unmute/posts/from/follow",
        "/user/unmute/stories/from/follow",
    } & set(paths)


@pytest.mark.asyncio
async def test_openapi_uses_client_friendly_schema_names():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    schema_names = set(schema["components"]["schemas"])
    assert not [name for name in schema_names if name.startswith("Body_")]
    assert not [name for name in schema_names if "_" in name]
    assert {
        "AuthLoginRequest",
        "AuthLoginBySessionIdRequest",
        "AuthSettingsRequest",
        "AccountPictureRequest",
        "DirectMessageRequest",
        "StoryUploadRequest",
        "StoryUploadByUrlRequest",
        "ClipUploadByUrlRequest",
    } <= schema_names

    operation_ids = [
        operation["operationId"]
        for methods in schema["paths"].values()
        for operation in methods.values()
    ]
    assert not [operation_id for operation_id in operation_ids if "_" in operation_id]
    assert "postStoryUploadByUrl" in operation_ids


@pytest.mark.asyncio
async def test_openapi_uses_human_friendly_tag_names():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    operation_tags = {
        tag
        for methods in schema["paths"].values()
        for operation in methods.values()
        for tag in operation["tags"]
    }
    assert operation_tags == {
        "Album (Carousel)",
        "Auth",
        "Clip (Reels)",
        "IGTV (Legacy)",
        "Insights",
        "Account",
        "Direct",
        "Hashtag",
        "Highlight",
        "Location",
        "Media",
        "Note",
        "Notifications",
        "Photo",
        "Story",
        "System",
        "User",
        "Video",
    }
    assert [tag["name"] for tag in schema["tags"]] == [
        "Auth",
        "Account",
        "User",
        "Media",
        "Direct",
        "Hashtag",
        "Location",
        "Highlight",
        "Note",
        "Notifications",
        "Photo",
        "Video",
        "Clip (Reels)",
        "Album (Carousel)",
        "Story",
        "IGTV (Legacy)",
        "Insights",
        "System",
    ]


@pytest.mark.asyncio
async def test_openapi_uses_human_friendly_operation_summaries():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert paths["/auth/login"]["post"]["summary"] == "Log in with username and password"
    assert paths["/auth/login/by/sessionid"]["post"]["summary"] == "Create a session from an existing session ID"
    assert paths["/auth/settings"]["get"]["summary"] == "Get saved auth settings"
    assert paths["/auth/settings"]["patch"]["summary"] == "Save auth settings"
    assert paths["/media/user/medias"]["get"]["summary"] == "List paginated user media"
    assert paths["/user/info/by/username"]["get"]["summary"] == "Get user profile by username"
    assert paths["/story/upload/by/url"]["post"]["summary"] == "Upload a story from a URL"
    assert paths["/clip/upload/by/url"]["post"]["summary"] == "Upload a Reel from a URL"
    assert paths["/album/download/by/urls"]["get"]["summary"] == "Download carousel album media from URLs"
    assert paths["/build"]["get"]["summary"] == "Get build metadata"
    assert paths["/deps"]["get"]["summary"] == "Get dependency versions"
    assert paths["/health"]["get"]["summary"] == "Check liveness"
    assert paths["/igtv/download"]["get"]["summary"] == "Download legacy IGTV video"
    assert paths["/insights/media/feed/all"]["get"]["summary"] == "Get account media insights feed"
    assert paths["/metrics"]["get"]["summary"] == "Get Prometheus metrics"
    assert paths["/ready"]["get"]["summary"] == "Check readiness"

    summaries = [
        operation["summary"]
        for methods in paths.values()
        for operation in methods.values()
    ]
    assert not [summary for summary in summaries if "By Url" in summary]
    assert not [summary for summary in summaries if "By Urls" in summary]
    assert not [summary for summary in summaries if "Sessionid" in summary]
    assert not [summary for summary in summaries if "Igtv" in summary]


@pytest.mark.asyncio
async def test_deps_returns_none_when_package_missing(monkeypatch):
    def fake_version(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr(main, "package_version", fake_version)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/deps")
    assert response.status_code == 200
    assert response.json() == {name: None for name in main.DEPENDENCY_PACKAGES}


@pytest.mark.asyncio
async def test_exception_handler_wraps_errors_in_envelope(monkeypatch):
    from dependencies import get_clients

    class BoomStorage:
        async def get(self, sessionid):
            raise RuntimeError("kapow")

        def close(self):
            pass

    app.dependency_overrides[get_clients] = lambda: BoomStorage()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/auth/timeline/feed", params={"sessionid": "x"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "kapow"
    assert body["exc_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_authorized_routes_accept_sessionid_header(monkeypatch):
    from dependencies import get_clients

    class HeaderStorage:
        def __init__(self):
            self.seen_sessionid = None

        async def get(self, sessionid):
            self.seen_sessionid = sessionid

            class Client:
                async def get_timeline_feed(self):
                    return {"feed": []}

            return Client()

        def close(self):
            pass

    storage = HeaderStorage()
    app.dependency_overrides[get_clients] = lambda: storage
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/auth/timeline/feed", headers={"X-Session-ID": "sid-from-header"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"feed": []}
    assert storage.seen_sessionid == "sid-from-header"


@pytest.mark.asyncio
async def test_authorized_routes_accept_sessionid_cookie(monkeypatch):
    from dependencies import get_clients

    class CookieStorage:
        def __init__(self):
            self.seen_sessionid = None

        async def get(self, sessionid):
            self.seen_sessionid = sessionid

            class Client:
                async def get_timeline_feed(self):
                    return {"feed": []}

            return Client()

        def close(self):
            pass

    storage = CookieStorage()
    app.dependency_overrides[get_clients] = lambda: storage
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ac.cookies.set("sessionid", "sid-from-cookie")
            response = await ac.get("/auth/timeline/feed")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"feed": []}
    assert storage.seen_sessionid == "sid-from-cookie"


@pytest.mark.asyncio
async def test_authorized_routes_reject_missing_sessionid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/auth/timeline/feed")

    assert response.status_code == 401
    assert response.json() == {"detail": "Session ID required"}


def test_custom_openapi_caches_schema():
    first = app.openapi()
    second = app.openapi()
    assert first is second
