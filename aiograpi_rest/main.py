import os
import platform
import re
import subprocess
import time
import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

from aiograpi import exceptions as aiograpi_exceptions
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse, RedirectResponse, Response

from aiograpi_rest.routers import (
    account,
    album,
    auth,
    clip,
    direct,
    hashtag,
    highlight,
    igtv,
    insights,
    location,
    media,
    note,
    notifications,
    photo,
    search,
    story,
    user,
    video,
)
from aiograpi_rest.storages import ClientStorage

APP_PACKAGE_NAME = "aiograpi-rest"


def _project_version(pyproject_path: Path | None = None) -> str | None:
    if pyproject_path is not None:
        paths = [pyproject_path]
    else:
        paths = [
            Path(__file__).with_name("pyproject.toml"),
            Path(__file__).resolve().parents[1] / "pyproject.toml",
        ]
    for path in paths:
        if path.exists():
            return tomllib.loads(path.read_text())["project"]["version"]
    return None


def _app_version() -> str:
    project_version = _project_version()
    if project_version:
        return project_version
    try:
        return package_version(APP_PACKAGE_NAME)
    except PackageNotFoundError:
        return "0+unknown"


APP_VERSION = _app_version()
APP_STARTED_AT = time.monotonic()
_TOKEN_OVERRIDES = {
    "id": "Id",
    "igtv": "Igtv",
    "pk": "Pk",
    "sessionid": "SessionId",
    "totp": "Totp",
    "url": "Url",
}
_HTTP_METHOD_PREFIXES = {"delete", "get", "patch", "post", "put"}
DEPENDENCY_PACKAGES = (
    "aiograpi",
    "fastapi",
    "pydantic",
    "starlette",
    "uvicorn",
    "tinydb",
    "requests",
    "aiofiles",
    "python-multipart",
)
OPENAPI_VERSION = "3.0.3"
OPENAPI_DESCRIPTION = """
RESTful HTTP service for `aiograpi`, the async Instagram Private API wrapper.

- [GitHub subzeroid/aiograpi-rest](https://github.com/subzeroid/aiograpi-rest)
- [HikerAPI with 100 free requests](https://hikerapi.com/p/7RAo9ACK)
""".strip()
OPENAPI_TAGS = [
    {"name": "Auth", "description": "Login, session settings, and relogin operations."},
    {"name": "Account", "description": "Authenticated account profile and privacy operations."},
    {"name": "User", "description": "Profile lookup and user relationship operations."},
    {"name": "Search", "description": "Cross-resource search operations."},
    {"name": "Media (Post)", "description": "Generic media/post lookup, edits, and interactions."},
    {"name": "Direct", "description": "Instagram Direct inbox, thread, and message operations."},
    {"name": "Hashtag", "description": "Hashtag lookup, media discovery, and follow operations."},
    {"name": "Location", "description": "Location lookup and media discovery operations."},
    {"name": "Highlight", "description": "Story highlight lookup and management operations."},
    {"name": "Note", "description": "Instagram Notes lookup and management operations."},
    {"name": "Notifications", "description": "Notification inbox and settings operations."},
    {"name": "Photo", "description": "Feed photo download and upload operations."},
    {"name": "Video", "description": "Feed video download and upload operations."},
    {"name": "Clip (Reels)", "description": "Instagram Reels clip download and upload operations."},
    {"name": "Album (Carousel)", "description": "Carousel album download and upload operations."},
    {"name": "Story", "description": "Story lookup, upload, download, and interactions."},
    {"name": "IGTV (Legacy)", "description": "Legacy IGTV operations still exposed by aiograpi."},
    {"name": "Insights", "description": "Account and media insights."},
    {"name": "System", "description": "Runtime service metadata."},
]
OPERATION_SUMMARIES = {
    "postAuthLogin": "Log in with username and password",
    "postAuthLoginBySessionId": "Create a session from an existing session ID",
    "patchAuthRelogin": "Refresh the current login session",
    "getAuthSettings": "Get saved auth settings",
    "patchAuthSettings": "Save auth settings",
    "postAuthTotp": "Enable TOTP two-factor authentication",
    "deleteAuthTotp": "Disable TOTP two-factor authentication",
    "postAuthChallengeResolve": "Resolve an Instagram login challenge",
    "getAccount": "Get authenticated account info",
    "getAccountFeedTimeline": "Get authenticated timeline feed",
    "getAccountFollowRequests": "List paginated pending follow requests",
    "getAccountLikedMedia": "List media liked by the authenticated account",
    "patchAccount": "Update authenticated account profile",
    "patchAccountPicture": "Update authenticated account picture",
    "patchAccountPrivacy": "Set authenticated account privacy",
    "getMedia": "Get media details",
    "getUserPosts": "List paginated user posts",
    "getUserTaggedPosts": "List paginated tagged posts",
    "getUserReels": "List paginated user Reels",
    "getUserVideos": "List paginated user videos",
    "deleteMedia": "Delete media",
    "patchMedia": "Edit media caption",
    "getMediaAuthor": "Get media author",
    "getMediaOembed": "Get media oEmbed data",
    "postMediaLike": "Like media",
    "deleteMediaLike": "Unlike media",
    "patchMediaSeen": "Mark media as seen",
    "getMediaLikers": "List media likers",
    "postMediaArchive": "Archive media",
    "deleteMediaArchive": "Unarchive media",
    "getMediaComments": "List media comments",
    "postMediaComment": "Create a media comment",
    "deleteMediaComment": "Delete a media comment",
    "getMediaCommentReplies": "List media comment replies",
    "postMediaCommentLike": "Like a media comment",
    "deleteMediaCommentLike": "Unlike a media comment",
    "postMediaSave": "Save media",
    "deleteMediaSave": "Unsave media",
    "postMediaPin": "Pin media",
    "deleteMediaPin": "Unpin media",
    "getDirectInbox": "List paginated direct inbox threads",
    "getDirectThread": "Get direct thread details",
    "postDirectThread": "Create a direct thread",
    "postDirectMessage": "Send a direct message",
    "deleteDirectMessage": "Delete a direct message",
    "patchDirectMessageSeen": "Mark a direct message as seen",
    "getHashtag": "Get hashtag details",
    "getHashtagMediaTop": "List paginated top hashtag media",
    "getHashtagMediaRecent": "List paginated recent hashtag media",
    "postHashtagFollow": "Follow a hashtag",
    "deleteHashtagFollow": "Unfollow a hashtag",
    "getLocation": "Get location details",
    "getLocationMediaTop": "List paginated top location media",
    "getLocationMediaRecent": "List paginated recent location media",
    "getSearchAccounts": "Search accounts",
    "getSearchFollowers": "Search a user's followers",
    "getSearchFollowing": "Search accounts a user follows",
    "getSearchHashtags": "Search hashtags",
    "getSearchUsers": "Search users",
    "getSearchLocations": "Search locations",
    "getSearchMusic": "Search music tracks",
    "getSearchPlaces": "Search places",
    "getSearchRecent": "List recent searches",
    "getSearchReels": "Search Reels",
    "getSearchTop": "Search top results",
    "getSearchTypeahead": "Get search autocomplete suggestions",
    "getPhotoDownload": "Download feed photo",
    "getPhotoDownloadByUrl": "Download feed photo from a URL",
    "postPhotoUpload": "Upload a feed photo",
    "postPhotoUploadByUrl": "Upload a feed photo from a URL",
    "getVideoDownload": "Download feed video",
    "getVideoDownloadByUrl": "Download feed video from a URL",
    "postVideoUpload": "Upload a feed video",
    "postVideoUploadByUrl": "Upload a feed video from a URL",
    "getIgtvDownload": "Download legacy IGTV video",
    "getIgtvDownloadByUrl": "Download legacy IGTV video from a URL",
    "postIgtvUpload": "Upload legacy IGTV video",
    "postIgtvUploadByUrl": "Upload legacy IGTV video from a URL",
    "getClipDownload": "Download a Reel",
    "getClipDownloadByUrl": "Download a Reel from a URL",
    "postClipUpload": "Upload a Reel",
    "postClipUploadByUrl": "Upload a Reel from a URL",
    "getAlbumDownload": "Download carousel album media",
    "getAlbumDownloadByUrls": "Download carousel album media from URLs",
    "postAlbumUpload": "Upload a carousel album",
    "postStoryUpload": "Upload a story",
    "postStoryUploadByUrl": "Upload a story from a URL",
    "getUserStories": "List user stories",
    "getStory": "Get story details",
    "deleteStory": "Delete a story",
    "patchStorySeen": "Mark stories as seen",
    "postStoryLike": "Like a story",
    "deleteStoryLike": "Unlike a story",
    "getStoryViewers": "List paginated story viewers",
    "getStoryArchive": "List paginated story archive days",
    "getStoryDownload": "Download story media",
    "getStoryDownloadByUrl": "Download story media from a URL",
    "getUser": "Get user profile",
    "getUserFollowers": "List paginated user followers",
    "getUserFollowing": "List paginated accounts a user follows",
    "getUserAbout": "Get user about details",
    "postUserFollow": "Follow a user",
    "deleteUserFollow": "Unfollow a user",
    "deleteUserFollower": "Remove a follower",
    "postUserMutePosts": "Mute posts from a followed user",
    "deleteUserMutePosts": "Unmute posts from a followed user",
    "postUserMuteStories": "Mute stories from a followed user",
    "deleteUserMuteStories": "Unmute stories from a followed user",
    "getUserFriendship": "Get user relationship",
    "postUserBlock": "Block a user",
    "deleteUserBlock": "Unblock a user",
    "getUserHighlights": "List user highlights",
    "getHighlight": "Get highlight details",
    "postHighlight": "Create a highlight",
    "patchHighlight": "Update a highlight",
    "deleteHighlight": "Delete a highlight",
    "postHighlightStory": "Add stories to a highlight",
    "deleteHighlightStory": "Remove stories from a highlight",
    "getNotifications": "Get notification inbox",
    "getNotificationsSettings": "Get supported notification settings",
    "patchNotificationsSettings": "Update notification settings",
    "getNotes": "List notes",
    "postNote": "Create a note",
    "deleteNote": "Delete a note",
    "getInsightsMediaFeed": "Get account media insights feed",
    "getInsightsAccount": "Get account insights",
    "getInsightsMedia": "Get media insights",
    "getBuild": "Get build metadata",
    "getDeps": "Get dependency versions",
    "getHealth": "Check liveness",
    "getMetrics": "Get Prometheus metrics",
    "getReady": "Check readiness",
}


def _word_to_pascal(word: str) -> str:
    return _TOKEN_OVERRIDES.get(word, word[:1].upper() + word[1:])


def _path_words(path: str) -> list[str]:
    words: list[str] = []
    for segment in path.strip("/").split("/"):
        segment = segment.strip("{}")
        words.extend(word for word in re.split(r"[_-]+", segment.lower()) if word)
    return words or ["root"]


def _to_pascal(words: list[str]) -> str:
    return "".join(_word_to_pascal(word) for word in words)


def _to_lower_camel(words: list[str]) -> str:
    pascal = _to_pascal(words)
    return pascal[:1].lower() + pascal[1:]


def generate_operation_id(route: APIRoute) -> str:
    assert route.methods
    method = sorted(route.methods)[0].lower()
    return _to_lower_camel([method, *_path_words(route.path_format)])


def _operation_id_words(operation_id: str) -> list[str]:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", operation_id).split()
    return [word.lower() for word in words]


def _request_schema_name(body_schema_name: str) -> str:
    words = _operation_id_words(body_schema_name.removeprefix("Body_"))
    if words and words[0] in _HTTP_METHOD_PREFIXES:
        words = words[1:]
    return f"{_to_pascal(words)}Request"


def _operation_schema_name(operation_id: str, suffix: str) -> str:
    words = _operation_id_words(operation_id)
    if words and words[0] in _HTTP_METHOD_PREFIXES:
        words = words[1:]
    return f"{_to_pascal(words)}{suffix}"


def _replace_schema_refs(value: Any, ref_replacements: dict[str, str]) -> None:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if ref in ref_replacements:
            value["$ref"] = ref_replacements[ref]
        for child in value.values():
            _replace_schema_refs(child, ref_replacements)
    elif isinstance(value, list):
        for item in value:
            _replace_schema_refs(item, ref_replacements)


def _rename_generated_body_schemas(openapi_schema: dict[str, Any]) -> None:
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    ref_replacements: dict[str, str] = {}
    for old_name in list(schemas):
        if not old_name.startswith("Body_"):
            continue
        new_name = _request_schema_name(old_name)
        schemas[new_name] = schemas.pop(old_name)
        schemas[new_name]["title"] = new_name
        ref_replacements[f"#/components/schemas/{old_name}"] = f"#/components/schemas/{new_name}"
    _replace_schema_refs(openapi_schema, ref_replacements)


def _extract_inline_response_schemas(openapi_schema: dict[str, Any]) -> None:
    schemas = openapi_schema.setdefault("components", {}).setdefault("schemas", {})
    for methods in openapi_schema.get("paths", {}).values():
        for operation in methods.values():
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if not operation_id:
                continue
            responses = operation.get("responses", {})
            for response in responses.values():
                content = response.get("content", {})
                for media in content.values():
                    schema = media.get("schema")
                    if not isinstance(schema, dict) or "$ref" in schema:
                        continue
                    title = str(schema.get("title", ""))
                    if not title.startswith("Response "):
                        continue
                    name = _operation_schema_name(operation_id, "Response")
                    schemas[name] = {**schema, "title": name}
                    media["schema"] = {"$ref": f"#/components/schemas/{name}"}


def _is_null_schema(schema: Any) -> bool:
    return isinstance(schema, dict) and schema.get("type") == "null" and len(schema) == 1


def _as_nullable_schema(schema: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        return {"allOf": [schema], "nullable": True}
    return {**schema, "nullable": True}


def _convert_nullable_schemas_to_openapi_30(value: Any) -> None:
    if isinstance(value, dict):
        value.pop("contentEncoding", None)
        value.pop("contentMediaType", None)

        any_of = value.get("anyOf")
        if isinstance(any_of, list) and any(_is_null_schema(item) for item in any_of):
            siblings = {key: item for key, item in value.items() if key != "anyOf"}
            non_null = [item for item in any_of if not _is_null_schema(item)]
            if len(non_null) == 1 and isinstance(non_null[0], dict):
                nullable_schema = _as_nullable_schema(non_null[0])
                value.clear()
                value.update({**nullable_schema, **siblings, "nullable": True})
            else:
                value["anyOf"] = non_null
                value["nullable"] = True

        schema_type = value.get("type")
        if isinstance(schema_type, list) and "null" in schema_type:
            non_null_types = [item for item in schema_type if item != "null"]
            if len(non_null_types) == 1:
                value["type"] = non_null_types[0]
            else:
                value["type"] = non_null_types
            value["nullable"] = True

        value.pop("contentEncoding", None)
        value.pop("contentMediaType", None)

        for child in value.values():
            _convert_nullable_schemas_to_openapi_30(child)
    elif isinstance(value, list):
        for item in value:
            _convert_nullable_schemas_to_openapi_30(item)


def _polish_operation_summaries(openapi_schema: dict[str, Any]) -> None:
    for methods in openapi_schema.get("paths", {}).values():
        for operation in methods.values():
            summary = OPERATION_SUMMARIES.get(operation.get("operationId"))
            if summary:
                operation["summary"] = summary


def _move_paths_after(openapi_schema: dict[str, Any], anchor_path: str, moved_paths: list[str]) -> None:
    paths = openapi_schema.get("paths")
    if not isinstance(paths, dict) or anchor_path not in paths:
        return

    moved = [(path, paths[path]) for path in moved_paths if path in paths]
    if not moved:
        return

    moved_names = {path for path, _ in moved}
    reordered = {}
    for path, methods in paths.items():
        if path in moved_names:
            continue
        reordered[path] = methods
        if path == anchor_path:
            reordered.update(moved)

    paths.clear()
    paths.update(reordered)


def _order_openapi_paths(openapi_schema: dict[str, Any]) -> None:
    _move_paths_after(openapi_schema, "/user/videos", ["/user/highlights", "/user/stories"])


app = FastAPI(
    generate_unique_id_function=generate_operation_id,
    openapi_version=OPENAPI_VERSION,
    openapi_tags=OPENAPI_TAGS,
)
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(search.router)
app.include_router(media.router)
app.include_router(media.user_router)
app.include_router(direct.router)
app.include_router(hashtag.router)
app.include_router(location.router)
app.include_router(highlight.router)
app.include_router(note.router)
app.include_router(notifications.router)
app.include_router(video.router)
app.include_router(photo.router)
app.include_router(user.router)
app.include_router(igtv.router)
app.include_router(clip.router)
app.include_router(album.router)
app.include_router(story.router)
app.include_router(story.user_router)
app.include_router(insights.router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect to /docs
    """
    return RedirectResponse(url="/docs")


def _dependency_versions() -> dict[str, str | None]:
    versions = {}
    for name in DEPENDENCY_PACKAGES:
        try:
            versions[name] = package_version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions


def _storage_readiness() -> dict[str, str]:
    clients = None
    try:
        clients = ClientStorage()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
    finally:
        if clients is not None:
            clients.close()


def _dependency_readiness() -> dict[str, Any]:
    versions = _dependency_versions()
    missing = [name for name, version in versions.items() if version is None]
    return {
        "status": "ok" if not missing else "error",
        "missing": missing,
    }


def _git_sha() -> str | None:
    env_sha = os.getenv("GIT_SHA") or os.getenv("COMMIT_SHA") or os.getenv("SOURCE_VERSION")
    if env_sha:
        return env_sha
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def _build_metadata() -> dict[str, str | None]:
    return {
        "name": "aiograpi-rest",
        "version": APP_VERSION,
        "python_version": platform.python_version(),
        "git_sha": _git_sha(),
        "build_time": os.getenv("BUILD_TIME"),
    }


def _metric_label_value(value: str | None) -> str:
    return str(value or "unknown").replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _metrics_text() -> str:
    build = _build_metadata()
    deps = _dependency_versions()
    uptime_seconds = max(0.0, time.monotonic() - APP_STARTED_AT)
    info_labels = ",".join(
        f'{key}="{_metric_label_value(value)}"'
        for key, value in (
            ("version", build["version"]),
            ("python_version", build["python_version"]),
            ("git_sha", build["git_sha"]),
            ("build_time", build["build_time"]),
        )
    )
    lines = [
        "# HELP aiograpi_rest_info Service build information.",
        "# TYPE aiograpi_rest_info gauge",
        f"aiograpi_rest_info{{{info_labels}}} 1",
        "# HELP aiograpi_rest_uptime_seconds Seconds since service start.",
        "# TYPE aiograpi_rest_uptime_seconds gauge",
        f"aiograpi_rest_uptime_seconds {uptime_seconds:.3f}",
        "# HELP aiograpi_rest_dependency_info Installed dependency versions.",
        "# TYPE aiograpi_rest_dependency_info gauge",
    ]
    for name, version in deps.items():
        installed = "1" if version else "0"
        labels = f'name="{_metric_label_value(name)}",version="{_metric_label_value(version)}"'
        lines.append(f"aiograpi_rest_dependency_info{{{labels}}} {installed}")
    return "\n".join(lines) + "\n"


@app.get("/health", tags=["System"], summary="Check liveness")
async def health():
    """Check liveness
    """
    return {"status": "ok"}


@app.get("/ready", tags=["System"], summary="Check readiness")
async def ready():
    """Check readiness
    """
    checks = {
        "storage": _storage_readiness(),
        "dependencies": _dependency_readiness(),
    }
    status = "ok" if all(check["status"] == "ok" for check in checks.values()) else "error"
    return JSONResponse({"status": status, "checks": checks}, status_code=200 if status == "ok" else 503)


@app.get("/metrics", tags=["System"], summary="Get Prometheus metrics")
async def metrics():
    """Get Prometheus metrics
    """
    return Response(_metrics_text(), media_type="text/plain; version=0.0.4")


@app.get("/build", tags=["System"], summary="Get build metadata")
async def build():
    """Get build metadata
    """
    return _build_metadata()


@app.get("/deps", tags=["System"], summary="Get dependency versions")
async def deps():
    """Get dependency versions
    """
    return _dependency_versions()


@app.get("/version", include_in_schema=False)
async def version():
    """Compatibility alias for /deps
    """
    return _dependency_versions()


@app.exception_handler(Exception)
async def handle_exception(request, exc: Exception):
    body = {
        "detail": str(exc),
        "exc_type": str(type(exc).__name__),
    }
    status_code = 500
    if isinstance(exc, aiograpi_exceptions.TwoFactorRequired):
        status_code = 401
        body["hint"] = "Retry POST /auth/login with verification_code."
    elif isinstance(exc, aiograpi_exceptions.ChallengeRequired):
        status_code = 403
        if "Challenge code required" in str(exc):
            body["hint"] = "Retry POST /auth/challenge/resolve with last_json and security_code."
        else:
            body["hint"] = "Resolve the Instagram challenge, then retry login or import a saved session."
    elif isinstance(
        exc,
        (
            aiograpi_exceptions.FeedbackRequired,
            aiograpi_exceptions.PleaseWaitFewMinutes,
            aiograpi_exceptions.RateLimitError,
        ),
    ):
        status_code = 429
        body["hint"] = (
            "Instagram is throttling this account/action. Pause automation, reduce request rate, "
            "check account and proxy health, then retry later."
        )
    elif isinstance(exc, aiograpi_exceptions.UnknownError) and "The username you entered" in str(exc):
        status_code = 401
        body["hint"] = "Check the Instagram username and retry POST /auth/login."
    return JSONResponse(body, status_code=status_code)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    # for route in app.routes:
    #     body_field = getattr(route, 'body_field', None)
    #     if body_field:
    #         body_field.type_.__name__ = 'name'
    openapi_schema = get_openapi(
        title="aiograpi-rest",
        version=APP_VERSION,
        description=OPENAPI_DESCRIPTION,
        routes=app.routes,
        tags=OPENAPI_TAGS,
        openapi_version=OPENAPI_VERSION,
    )
    _rename_generated_body_schemas(openapi_schema)
    _extract_inline_response_schemas(openapi_schema)
    _convert_nullable_schemas_to_openapi_30(openapi_schema)
    _polish_operation_summaries(openapi_schema)
    _order_openapi_paths(openapi_schema)
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
