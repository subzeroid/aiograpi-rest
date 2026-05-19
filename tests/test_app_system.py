import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import aiograpi.exceptions as aiograpi_exceptions
import pytest
from httpx import ASGITransport, AsyncClient

import aiograpi_rest.main as main
from aiograpi_rest.main import app

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
        "/account": {"get", "patch"},
        "/account/collection": {"get"},
        "/account/collection/media": {"get"},
        "/account/collections": {"get"},
        "/account/feed/timeline": {"get"},
        "/account/follow/requests": {"get"},
        "/account/picture": {"patch"},
        "/account/privacy": {"patch"},
        "/album/download": {"get"},
        "/album/download/by/urls": {"get"},
        "/album/upload": {"post"},
        "/auth/challenge/resolve": {"post"},
        "/auth/login": {"post"},
        "/auth/login/by/sessionid": {"post"},
        "/auth/relogin": {"patch"},
        "/auth/settings": {"get", "patch"},
        "/auth/totp": {"delete", "post"},
        "/build": {"get"},
        "/clip/download": {"get"},
        "/clip/download/by/url": {"get"},
        "/clip/upload": {"post"},
        "/clip/upload/by/url": {"post"},
        "/deps": {"get"},
        "/direct/file": {"post"},
        "/direct/inbox": {"get"},
        "/direct/media": {"get", "post"},
        "/direct/message": {"delete", "get", "post"},
        "/direct/message/like": {"delete", "post"},
        "/direct/message/reaction": {"delete", "post"},
        "/direct/message/seen": {"patch"},
        "/direct/messages": {"get"},
        "/direct/messages/search": {"get"},
        "/direct/pending": {"get", "patch"},
        "/direct/photo": {"post"},
        "/direct/presence": {"get"},
        "/direct/profile": {"post"},
        "/direct/requests": {"get"},
        "/direct/search": {"get"},
        "/direct/spam": {"get"},
        "/direct/story": {"post"},
        "/direct/thread": {"delete", "get", "patch", "post"},
        "/direct/thread/by/participants": {"get"},
        "/direct/thread/mute": {"delete", "post"},
        "/direct/thread/seen": {"patch"},
        "/direct/thread/user": {"post"},
        "/direct/thread/video/call/mute": {"delete", "post"},
        "/direct/threads": {"get"},
        "/direct/video": {"post"},
        "/direct/voice": {"post"},
        "/explore": {"get"},
        "/explore/media": {"get"},
        "/hashtag": {"get"},
        "/hashtag/follow": {"delete", "post"},
        "/hashtag/media/recent": {"get"},
        "/hashtag/media/top": {"get"},
        "/hashtag/related": {"get"},
        "/hashtag/reels": {"get"},
        "/highlight": {"delete", "get", "patch", "post"},
        "/highlight/story": {"delete", "post"},
        "/health": {"get"},
        "/igtv/download": {"get"},
        "/igtv/download/by/url": {"get"},
        "/igtv/upload": {"post"},
        "/igtv/upload/by/url": {"post"},
        "/insights/account": {"get"},
        "/insights/media": {"get"},
        "/insights/media/feed": {"get"},
        "/location": {"get"},
        "/location/guides": {"get"},
        "/location/media/recent": {"get"},
        "/location/media/top": {"get"},
        "/metrics": {"get"},
        "/media": {"delete", "get", "patch"},
        "/media/archive": {"delete", "post"},
        "/media/comment": {"delete", "post"},
        "/media/comment/like": {"delete", "post"},
        "/media/comment/replies": {"get"},
        "/media/comments": {"get"},
        "/media/like": {"delete", "post"},
        "/account/liked/media": {"get"},
        "/media/likers": {"get"},
        "/media/oembed": {"get"},
        "/media/pin": {"delete", "post"},
        "/media/save": {"delete", "post"},
        "/media/seen": {"patch"},
        "/media/author": {"get"},
        "/music/feed/browser": {"get"},
        "/note": {"delete", "post"},
        "/notes": {"get"},
        "/notifications": {"get"},
        "/notifications/settings": {"get", "patch"},
        "/photo/download": {"get"},
        "/photo/download/by/url": {"get"},
        "/photo/upload": {"post"},
        "/photo/upload/by/url": {"post"},
        "/ready": {"get"},
        "/reels": {"get"},
        "/reels/explore": {"get"},
        "/reels/friends": {"get"},
        "/reels/timeline": {"get"},
        "/search/accounts": {"get"},
        "/search/followers": {"get"},
        "/search/following": {"get"},
        "/search/hashtags": {"get"},
        "/search/locations": {"get"},
        "/search/music": {"get"},
        "/search/places": {"get"},
        "/search/recent": {"get"},
        "/search/reels": {"get"},
        "/search/top": {"get"},
        "/search/typeahead": {"get"},
        "/search/users": {"get"},
        "/story": {"delete", "get"},
        "/story/archive": {"get"},
        "/story/download": {"get"},
        "/story/download/by/url": {"get"},
        "/story/like": {"delete", "post"},
        "/story/seen": {"patch"},
        "/story/upload": {"post"},
        "/story/upload/by/url": {"post"},
        "/story/viewers": {"get"},
        "/track": {"get"},
        "/track/download/by/url": {"get"},
        "/track/stream": {"get"},
        "/user": {"get"},
        "/user/about": {"get"},
        "/user/block": {"delete", "post"},
        "/user/follower": {"delete"},
        "/user/followers": {"get"},
        "/user/following": {"get"},
        "/user/friendship": {"get"},
        "/user/guides": {"get"},
        "/user/highlights": {"get"},
        "/user/posts": {"get"},
        "/user/pinned/posts": {"get"},
        "/user/mute/posts": {"delete", "post"},
        "/user/mute/stories": {"delete", "post"},
        "/user/follow": {"delete", "post"},
        "/user/reels": {"get"},
        "/user/stories": {"get"},
        "/user/tagged/posts": {"get"},
        "/user/videos": {"get"},
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
async def test_openapi_orders_user_story_collections_after_user_videos():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    paths = list(response.json()["paths"])
    start = paths.index("/user/videos")
    assert paths[start : start + 5] == [
        "/user/videos",
        "/user/pinned/posts",
        "/user/highlights",
        "/user/stories",
        "/user/guides",
    ]


@pytest.mark.asyncio
async def test_openapi_removes_undo_style_paths():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert not {
        "/media/delete",
        "/media/edit",
        "/media/id",
        "/media/unarchive",
        "/media/unlike",
        "/media/pk",
        "/media/pk/from/code",
        "/media/pk/from/url",
        "/account/info",
        "/account/profile",
        "/account/follow/request",
        "/auth/timeline/feed",
        "/auth/totp/enable",
        "/story/delete",
        "/story/info",
        "/story/pk/from/url",
        "/story/unlike",
        "/story/viewer",
        "/story/user/stories",
        "/hashtag/info",
        "/hashtag/medias/recent",
        "/hashtag/medias/top",
        "/highlight/info",
        "/highlight/stories",
        "/location/info",
        "/location/medias/recent",
        "/location/medias/top",
        "/location/search",
        "/media/info",
        "/media/liked",
        "/media/comment/reply",
        "/media/liker",
        "/media/user",
        "/insights/media/feed/all",
        "/user/id/from/username",
        "/user/info",
        "/user/info/by/username",
        "/user/follow/requests",
        "/user/highlight",
        "/user/remove/follower",
        "/user/search",
        "/user/medias",
        "/user/media",
        "/user/clips",
        "/user/unfollow",
        "/user/unmute/posts/from/follow",
        "/user/unmute/stories/from/follow",
        "/user/tagged/medias",
        "/user/tagged/media",
        "/user/username/from/id",
        "/user/video",
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
        "Explore",
        "Hashtag",
        "Highlight",
        "Location",
        "Media (Post)",
        "Note",
        "Notifications",
        "Photo",
        "Reels",
        "Search",
        "Story",
        "System",
        "Track (Music)",
        "User",
        "Video",
    }
    assert [tag["name"] for tag in schema["tags"]] == [
        "Auth",
        "Account",
        "User",
        "Search",
        "Reels",
        "Explore",
        "Media (Post)",
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
        "Track (Music)",
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
    assert paths["/account"]["get"]["summary"] == "Get authenticated account info"
    assert paths["/account"]["patch"]["summary"] == "Update authenticated account profile"
    assert paths["/account/collections"]["get"]["summary"] == "List saved collections"
    assert paths["/account/collection"]["get"]["summary"] == "Get a saved collection"
    assert paths["/account/collection/media"]["get"]["summary"] == "List saved collection media"
    assert paths["/account/follow/requests"]["get"]["summary"] == "List paginated pending follow requests"
    assert paths["/direct/thread"]["patch"]["summary"] == "Update direct thread state"
    assert paths["/direct/thread/user"]["post"]["summary"] == "Add users to a direct thread"
    assert paths["/direct/thread/seen"]["patch"]["summary"] == "Mark a direct thread as seen"
    assert paths["/direct/thread/mute"]["post"]["summary"] == "Mute a direct thread"
    assert paths["/direct/thread/mute"]["delete"]["summary"] == "Unmute a direct thread"
    assert paths["/direct/thread/video/call/mute"]["post"]["summary"] == "Mute direct thread video calls"
    assert paths["/direct/thread/video/call/mute"]["delete"]["summary"] == "Unmute direct thread video calls"
    assert paths["/direct/thread/by/participants"]["get"]["summary"] == "Find a direct thread by participants"
    assert paths["/direct/message/like"]["post"]["summary"] == "Like a direct message"
    assert paths["/direct/message/reaction"]["delete"]["summary"] == "Remove a direct message reaction"
    assert paths["/direct/messages/search"]["get"]["summary"] == "Search direct messages"
    assert paths["/direct/pending"]["patch"]["summary"] == "Approve a pending direct thread request"
    assert paths["/direct/requests"]["get"]["summary"] == "List direct message requests"
    assert paths["/direct/spam"]["get"]["summary"] == "List paginated direct spam threads"
    assert paths["/direct/presence"]["get"]["summary"] == "Get direct presence"
    assert paths["/direct/media"]["get"]["summary"] == "List direct thread media"
    assert paths["/direct/media"]["post"]["summary"] == "Share media to direct users"
    assert paths["/direct/profile"]["post"]["summary"] == "Share a profile to direct users or threads"
    assert paths["/direct/story"]["post"]["summary"] == "Share a story to direct users or threads"
    assert paths["/direct/photo"]["post"]["summary"] == "Send a direct photo"
    assert paths["/direct/video"]["post"]["summary"] == "Send a direct video"
    assert paths["/direct/voice"]["post"]["summary"] == "Send a direct voice message"
    assert paths["/direct/file"]["post"]["summary"] == "Send a direct file"
    assert paths["/explore"]["get"]["summary"] == "Get Explore page"
    assert paths["/explore/media"]["get"]["summary"] == "Get Explore media details"
    assert paths["/hashtag"]["get"]["summary"] == "Get hashtag details"
    assert paths["/hashtag/media/top"]["get"]["summary"] == "List paginated top hashtag media"
    assert paths["/hashtag/related"]["get"]["summary"] == "List related hashtags"
    assert paths["/hashtag/reels"]["get"]["summary"] == "List hashtag Reels"
    assert paths["/highlight"]["get"]["summary"] == "Get highlight details"
    assert paths["/highlight/story"]["post"]["summary"] == "Add stories to a highlight"
    assert paths["/highlight/story"]["delete"]["summary"] == "Remove stories from a highlight"
    assert paths["/location"]["get"]["summary"] == "Get location details"
    assert paths["/location/guides"]["get"]["summary"] == "List location guides"
    assert paths["/location/media/recent"]["get"]["summary"] == "List paginated recent location media"
    assert paths["/media"]["get"]["summary"] == "Get media details"
    assert paths["/media/comments"]["get"]["summary"] == "List paginated media comments"
    assert paths["/media/comment/replies"]["get"]["summary"] == "List media comment replies"
    assert paths["/media/likers"]["get"]["summary"] == "List media likers"
    assert paths["/music/feed/browser"]["get"]["summary"] == "Get feed music browser"
    assert paths["/notes"]["get"]["summary"] == "List notes"
    assert paths["/reels"]["get"]["summary"] == "List connected Reels"
    assert paths["/reels/friends"]["get"]["summary"] == "List friends Reels"
    assert paths["/reels/explore"]["get"]["summary"] == "List explore Reels"
    assert paths["/reels/timeline"]["get"]["summary"] == "List Reels timeline media"
    assert paths["/search/accounts"]["get"]["summary"] == "Search accounts"
    assert paths["/search/followers"]["get"]["summary"] == "Search a user's followers"
    assert paths["/search/following"]["get"]["summary"] == "Search accounts a user follows"
    assert paths["/search/hashtags"]["get"]["summary"] == "Search hashtags"
    assert paths["/search/locations"]["get"]["summary"] == "Search locations"
    assert paths["/search/music"]["get"]["summary"] == "Search music tracks"
    assert paths["/search/places"]["get"]["summary"] == "Search places"
    assert paths["/search/recent"]["get"]["summary"] == "List recent searches"
    assert paths["/search/reels"]["get"]["summary"] == "Search Reels"
    assert paths["/search/top"]["get"]["summary"] == "Search top results"
    assert paths["/search/typeahead"]["get"]["summary"] == "Get search autocomplete suggestions"
    assert paths["/search/users"]["get"]["summary"] == "Search users"
    assert paths["/story"]["get"]["summary"] == "Get story details"
    assert paths["/story/viewers"]["get"]["summary"] == "List paginated story viewers"
    assert paths["/track"]["get"]["summary"] == "Get music track details"
    assert paths["/track/stream"]["get"]["summary"] == "Get track stream media"
    assert paths["/track/download/by/url"]["get"]["summary"] == "Download track audio from a URL"
    assert paths["/user"]["get"]["summary"] == "Get user profile"
    assert paths["/user/followers"]["get"]["summary"] == "List paginated user followers"
    assert paths["/user/guides"]["get"]["summary"] == "List user guides"
    assert paths["/user/highlights"]["get"]["summary"] == "List user highlights"
    assert paths["/user/pinned/posts"]["get"]["summary"] == "List user pinned posts"
    assert paths["/user/posts"]["get"]["summary"] == "List paginated user posts"
    assert paths["/user/reels"]["get"]["summary"] == "List paginated user Reels"
    assert paths["/user/stories"]["get"]["summary"] == "List user stories"
    assert paths["/user/tagged/posts"]["get"]["summary"] == "List paginated tagged posts"
    assert paths["/user/videos"]["get"]["summary"] == "List paginated user videos"
    assert paths["/story/upload/by/url"]["post"]["summary"] == "Upload a story from a URL"
    assert paths["/clip/upload/by/url"]["post"]["summary"] == "Upload a Reel from a URL"
    assert paths["/album/download/by/urls"]["get"]["summary"] == "Download carousel album media from URLs"
    assert paths["/build"]["get"]["summary"] == "Get build metadata"
    assert paths["/deps"]["get"]["summary"] == "Get dependency versions"
    assert paths["/health"]["get"]["summary"] == "Check liveness"
    assert paths["/igtv/download"]["get"]["summary"] == "Download legacy IGTV video"
    assert paths["/account/liked/media"]["get"]["summary"] == "List media liked by the authenticated account"
    assert paths["/account/feed/timeline"]["get"]["summary"] == "Get authenticated timeline feed"
    assert paths["/insights/media/feed"]["get"]["summary"] == "Get account media insights feed"
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
    from aiograpi_rest.dependencies import get_clients

    class BoomStorage:
        async def get(self, sessionid):
            raise RuntimeError("kapow")

        def close(self):
            pass

    app.dependency_overrides[get_clients] = lambda: BoomStorage()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/account/feed/timeline", params={"sessionid": "x"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "kapow"
    assert body["exc_type"] == "RuntimeError"


@pytest.mark.parametrize(
    "exc",
    [
        aiograpi_exceptions.FeedbackRequired("feedback_required"),
        aiograpi_exceptions.PleaseWaitFewMinutes("Please wait a few minutes before you try again."),
        aiograpi_exceptions.RateLimitError("rate limit exceeded"),
    ],
)
@pytest.mark.asyncio
async def test_exception_handler_maps_instagram_throttling_errors(monkeypatch, exc):
    from aiograpi_rest.dependencies import get_clients

    class BoomStorage:
        async def get(self, sessionid):
            raise exc

        def close(self):
            pass

    app.dependency_overrides[get_clients] = lambda: BoomStorage()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/account/feed/timeline", params={"sessionid": "x"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    body = response.json()
    assert body["detail"] == str(exc)
    assert body["exc_type"] == type(exc).__name__
    assert body["hint"] == (
        "Instagram is throttling this account/action. Pause automation, reduce request rate, "
        "check account and proxy health, then retry later."
    )


@pytest.mark.asyncio
async def test_auth_login_openapi_describes_verification_code():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    login_schema = schemas["AuthLoginRequest"]
    verification_code = login_schema["properties"]["verification_code"]
    assert "Two-factor" in verification_code["description"]
    assert "POST /auth/login" in verification_code["description"]


@pytest.mark.asyncio
async def test_story_upload_openapi_documents_json_encoded_form_mentions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    for schema_name in ("StoryUploadRequest", "StoryUploadByUrlRequest"):
        mentions = schemas[schema_name]["properties"]["mentions"]
        assert mentions["items"] == {"type": "string"}
        assert mentions["nullable"] is True


@pytest.mark.asyncio
async def test_upload_openapi_documents_json_encoded_form_usertags_and_location():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    for schema_name in (
        "PhotoUploadRequest",
        "PhotoUploadByUrlRequest",
        "VideoUploadRequest",
        "VideoUploadByUrlRequest",
        "ClipUploadRequest",
        "ClipUploadByUrlRequest",
        "IgtvUploadRequest",
        "IgtvUploadByUrlRequest",
        "AlbumUploadRequest",
        "MediaRequest",
    ):
        schema = schemas[schema_name]
        usertags = schema["properties"]["usertags"]
        location = schema["properties"]["location"]
        assert usertags["items"] == {"type": "string"}
        assert usertags["nullable"] is True
        assert location["type"] == "string"
        assert location["nullable"] is True


@pytest.mark.asyncio
async def test_authorized_routes_accept_sessionid_header(monkeypatch):
    from aiograpi_rest.dependencies import get_clients

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
            response = await ac.get("/account/feed/timeline", headers={"X-Session-ID": "sid-from-header"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"feed": []}
    assert storage.seen_sessionid == "sid-from-header"


@pytest.mark.asyncio
async def test_authorized_routes_accept_sessionid_cookie(monkeypatch):
    from aiograpi_rest.dependencies import get_clients

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
            response = await ac.get("/account/feed/timeline")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"feed": []}
    assert storage.seen_sessionid == "sid-from-cookie"


@pytest.mark.asyncio
async def test_authorized_routes_reject_missing_sessionid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/account/feed/timeline")

    assert response.status_code == 401
    assert response.json() == {"detail": "Session ID required"}


def test_custom_openapi_caches_schema():
    first = app.openapi()
    second = app.openapi()
    assert first is second


def test_openapi_path_order_helper_ignores_missing_inputs():
    schema_without_paths = {}
    main._move_paths_after(schema_without_paths, "/anchor", ["/moved"])
    assert schema_without_paths == {}

    schema_without_anchor = {"paths": {"/moved": {"get": {}}}}
    main._move_paths_after(schema_without_anchor, "/anchor", ["/moved"])
    assert list(schema_without_anchor["paths"]) == ["/moved"]

    schema_without_moved_paths = {"paths": {"/anchor": {"get": {}}, "/other": {"get": {}}}}
    main._move_paths_after(schema_without_moved_paths, "/anchor", ["/missing"])
    assert list(schema_without_moved_paths["paths"]) == ["/anchor", "/other"]
