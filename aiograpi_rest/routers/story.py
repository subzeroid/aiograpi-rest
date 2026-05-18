import json
from pathlib import Path
from typing import List, Optional

import requests
from aiograpi import Client
from aiograpi.types import (
    Story,
    StoryArchiveDay,
    StoryHashtag,
    StoryLink,
    StoryLocation,
    StoryMention,
    StorySticker,
    Viewer,
)
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import AnyHttpUrl, ValidationError

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.helpers import photo_upload_story_as_photo, photo_upload_story_as_video, video_upload_story

router = APIRouter(
    prefix="/story",
    tags=["Story"],
    responses={404: {"description": "Not found"}},
)

STORY_POSITION_DEFAULTS = {
    "x": 0.5,
    "y": 0.5,
    "width": 0.5,
    "height": 0.2,
    "rotation": 0.0,
}


def _url_points_to_video(url: AnyHttpUrl) -> bool:
    path = str(url).lower().split("?", 1)[0]
    return path.endswith((".mp4", ".mov", ".m4v"))


def _json_form_description(model_name: str) -> str:
    return (
        f"Repeat this form field with a JSON-encoded {model_name} object, "
        "or pass one JSON array of objects."
    )


def _with_story_position_defaults(item):
    fields = item.__class__.model_fields
    updates = {
        field: default
        for field, default in STORY_POSITION_DEFAULTS.items()
        if field in fields and getattr(item, field) is None
    }
    if not updates:
        return item
    return item.model_copy(update=updates)


def _parse_json_form_models(values, model, field_name: str):
    parsed = []
    for raw_value in values or []:
        try:
            payload = json.loads(raw_value)
            items = payload if isinstance(payload, list) else [payload]
            parsed.extend(_with_story_position_defaults(model.model_validate(item)) for item in items)
        except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid JSON object for form field '{field_name}'",
            ) from exc
    return parsed


async def _upload_story_content(cl, content, *, is_video, as_video, **kwargs):
    if is_video:
        return await video_upload_story(cl, content, **kwargs)
    if as_video:
        return await photo_upload_story_as_video(cl, content, **kwargs)
    return await photo_upload_story_as_photo(cl, content, **kwargs)


@router.post("/upload", response_model=Story)
async def story_upload(sessionid: str = Depends(get_sessionid),
                       file: UploadFile = File(...),
                       as_video: Optional[bool] = Form(False),
                       caption: Optional[str] = Form(""),
                       mentions: Optional[List[str]] = Form(
                           [], description=_json_form_description("StoryMention")
                       ),
                       locations: Optional[List[str]] = Form(
                           [], description=_json_form_description("StoryLocation")
                       ),
                       links: Optional[List[str]] = Form([], description=_json_form_description("StoryLink")),
                       hashtags: Optional[List[str]] = Form(
                           [], description=_json_form_description("StoryHashtag")
                       ),
                       stickers: Optional[List[str]] = Form(
                           [], description=_json_form_description("StorySticker")
                       ),
                       clients: ClientStorage = Depends(get_clients)) -> Story:
    """Upload photo or video to story
    """
    cl = await clients.get(sessionid)
    content = await file.read()
    return await _upload_story_content(
        cl, content,
        is_video=(file.content_type or "").startswith("video/"),
        as_video=as_video,
        caption=caption,
        mentions=_parse_json_form_models(mentions, StoryMention, "mentions"),
        links=_parse_json_form_models(links, StoryLink, "links"),
        hashtags=_parse_json_form_models(hashtags, StoryHashtag, "hashtags"),
        locations=_parse_json_form_models(locations, StoryLocation, "locations"),
        stickers=_parse_json_form_models(stickers, StorySticker, "stickers"))


@router.post("/upload/by/url", response_model=Story)
async def story_upload_by_url(sessionid: str = Depends(get_sessionid),
                              url: AnyHttpUrl = Form(...),
                              as_video: Optional[bool] = Form(False),
                              caption: Optional[str] = Form(""),
                              mentions: Optional[List[str]] = Form(
                                  [], description=_json_form_description("StoryMention")
                              ),
                              locations: Optional[List[str]] = Form(
                                  [], description=_json_form_description("StoryLocation")
                              ),
                              links: Optional[List[str]] = Form([], description=_json_form_description("StoryLink")),
                              hashtags: Optional[List[str]] = Form(
                                  [], description=_json_form_description("StoryHashtag")
                              ),
                              stickers: Optional[List[str]] = Form(
                                  [], description=_json_form_description("StorySticker")
                              ),
                              clients: ClientStorage = Depends(get_clients)) -> Story:
    """Upload photo or video to story by URL
    """
    cl = await clients.get(sessionid)
    content = requests.get(url).content
    return await _upload_story_content(
        cl, content,
        is_video=_url_points_to_video(url),
        as_video=as_video,
        caption=caption,
        mentions=_parse_json_form_models(mentions, StoryMention, "mentions"),
        links=_parse_json_form_models(links, StoryLink, "links"),
        hashtags=_parse_json_form_models(hashtags, StoryHashtag, "hashtags"),
        locations=_parse_json_form_models(locations, StoryLocation, "locations"),
        stickers=_parse_json_form_models(stickers, StorySticker, "stickers"))


@router.get("/user/stories", response_model=List[Story])
async def story_user_stories(sessionid: str = Depends(get_sessionid),
                            user_id: str = Query(...),
                            amount: Optional[int] = Query(None),
                            clients: ClientStorage = Depends(get_clients)) -> List[Story]:
    """Get a user's stories
    """
    cl = await clients.get(sessionid)
    return await cl.user_stories(user_id, amount)


@router.get("/info", response_model=Story)
async def story_info(sessionid: str = Depends(get_sessionid),
                     story_pk: int = Query(...),
                     use_cache: Optional[bool] = Query(True),
                     clients: ClientStorage = Depends(get_clients)) -> Story:
    """Get Story by pk or id
    """
    cl = await clients.get(sessionid)
    return await cl.story_info(story_pk, use_cache)


@router.delete("", response_model=bool)
async def story_delete(sessionid: str = Depends(get_sessionid),
                       story_pk: int = Query(...),
                       clients: ClientStorage = Depends(get_clients)) -> bool:
    """Delete story
    """
    cl = await clients.get(sessionid)
    return await cl.story_delete(story_pk)


@router.patch("/seen", response_model=bool)
async def story_seen(sessionid: str = Depends(get_sessionid),
                     story_pks: List[int] = Form(...),
                     skipped_story_pks: Optional[List[int]] = Form([]),
                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Mark a media as seen
    """
    cl = await clients.get(sessionid)
    return await cl.story_seen(story_pks, skipped_story_pks)

@router.post("/like", response_model=bool)
async def story_like(sessionid: str = Depends(get_sessionid),
                     story_id: str = Form(...),
                     revert: Optional[bool] = Form(False),
                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Like a Story
    """
    cl = await clients.get(sessionid)
    return await cl.story_like(story_id, revert)

@router.delete("/like", response_model=bool)
async def story_unlike(sessionid: str = Depends(get_sessionid),
                     story_id: str = Query(...),
                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unlike a Story
    """
    cl = await clients.get(sessionid)
    return await cl.story_unlike(story_id)


@router.get("/viewers", response_model=List[Viewer])
async def story_viewers(sessionid: str = Depends(get_sessionid),
                        story_pk: str = Query(...),
                        amount: Optional[int] = Query(0),
                        clients: ClientStorage = Depends(get_clients)) -> List[Viewer]:
    """Get story viewers
    """
    cl = await clients.get(sessionid)
    return await cl.story_viewers(story_pk, amount)


@router.get("/archive", response_model=List[StoryArchiveDay])
async def story_archive(sessionid: str = Depends(get_sessionid),
                        amount: Optional[int] = Query(0),
                        include_memories: Optional[bool] = Query(True),
                        clients: ClientStorage = Depends(get_clients)) -> List[StoryArchiveDay]:
    """Get story archive days
    """
    cl = await clients.get(sessionid)
    return await cl.archive_story_days(amount, include_memories)


@router.get("/pk/from/url")
async def story_pk_from_url(url: str) -> int:
    """Get Story (media) PK from URL
    """
    return Client().story_pk_from_url(url)


@router.get("/download")
async def story_download(sessionid: str = Depends(get_sessionid),
                         story_pk: int = Query(...),
                         filename: Optional[str] = Query(""),
                         folder: Optional[Path] = Query(""),
                         returnFile: Optional[bool] = Query(True),
                         clients: ClientStorage = Depends(get_clients)):
    """Download story media by media_type
    """
    cl = await clients.get(sessionid)
    result = await cl.story_download(story_pk, filename, folder)
    if returnFile:
        return FileResponse(result)
    else:
        return result


@router.get("/download/by/url")
async def story_download_by_url(sessionid: str = Depends(get_sessionid),
                                url: str = Query(...),
                                filename: Optional[str] = Query(""),
                                folder: Optional[Path] = Query(""),
                                returnFile: Optional[bool] = Query(True),
                                clients: ClientStorage = Depends(get_clients)):
    """Download story media using URL
    """
    cl = await clients.get(sessionid)
    result = await cl.story_download_by_url(url, filename, folder)
    if returnFile:
        return FileResponse(result)
    else:
        return result
