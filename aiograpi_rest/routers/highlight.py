import json
from typing import List, Optional

from aiograpi.types import Highlight
from fastapi import APIRouter, Depends, Form, HTTPException, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid

router = APIRouter(
    prefix="/highlight",
    tags=["Highlight"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=Highlight)
async def highlight(
    sessionid: str = Depends(get_sessionid),
    highlight_pk: str = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> Highlight:
    """Get highlight info
    """
    cl = await clients.get(sessionid)
    return await cl.highlight_info(highlight_pk)


@router.post("", response_model=Highlight)
async def highlight_create(
    sessionid: str = Depends(get_sessionid),
    title: str = Form(...),
    story_ids: List[str] = Form(...),
    cover_story_id: str = Form(""),
    crop_rect: List[float] = Form([0.0, 0.21830457, 1.0, 0.78094524]),
    clients: ClientStorage = Depends(get_clients),
) -> Highlight:
    """Create a highlight
    """
    cl = await clients.get(sessionid)
    return await cl.highlight_create(title, story_ids, cover_story_id, crop_rect)


@router.patch("", response_model=Highlight)
async def highlight_edit(
    sessionid: str = Depends(get_sessionid),
    highlight_pk: str = Form(...),
    title: str = Form(""),
    cover: Optional[str] = Form(None),
    added_media_ids: List[str] = Form([]),
    removed_media_ids: List[str] = Form([]),
    clients: ClientStorage = Depends(get_clients),
) -> Highlight:
    """Update a highlight
    """
    if cover:
        try:
            cover_data = json.loads(cover)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="cover must be valid JSON")
    else:
        cover_data = {}
    cl = await clients.get(sessionid)
    return await cl.highlight_edit(
        highlight_pk,
        title,
        cover_data,
        added_media_ids,
        removed_media_ids,
    )


@router.delete("", response_model=bool)
async def highlight_delete(
    sessionid: str = Depends(get_sessionid),
    highlight_pk: str = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Delete a highlight
    """
    cl = await clients.get(sessionid)
    return await cl.highlight_delete(highlight_pk)


@router.post("/story", response_model=Highlight)
async def highlight_story_add(
    sessionid: str = Depends(get_sessionid),
    highlight_pk: str = Form(...),
    story_ids: List[str] = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> Highlight:
    """Add stories to a highlight
    """
    cl = await clients.get(sessionid)
    return await cl.highlight_add_stories(highlight_pk, story_ids)


@router.delete("/story", response_model=Highlight)
async def highlight_story_remove(
    sessionid: str = Depends(get_sessionid),
    highlight_pk: str = Query(...),
    story_ids: List[str] = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> Highlight:
    """Remove stories from a highlight
    """
    cl = await clients.get(sessionid)
    return await cl.highlight_remove_stories(highlight_pk, story_ids)
