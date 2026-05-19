from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid

TAG = "Track (Music)"

router = APIRouter(
    prefix="/track",
    tags=[TAG],
    responses={404: {"description": "Not found"}},
)
music_router = APIRouter(
    prefix="/music",
    tags=[TAG],
    responses={404: {"description": "Not found"}},
)


def _ensure_single_track_selector(track_id: Optional[str], canonical_id: Optional[str]) -> None:
    if not track_id and not canonical_id:
        raise HTTPException(status_code=422, detail="Provide id or canonical_id")
    if track_id and canonical_id:
        raise HTTPException(status_code=422, detail="Provide only one of id or canonical_id")


@router.get("", response_model=Dict[str, Any])
async def track_info(
    sessionid: str = Depends(get_sessionid),
    track_id: Optional[str] = Query(None, alias="id"),
    canonical_id: Optional[str] = Query(None),
    max_id: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Get music track details
    """
    _ensure_single_track_selector(track_id, canonical_id)
    cl = await clients.get(sessionid)
    if canonical_id:
        return jsonable_encoder(await cl.track_info_by_canonical_id(canonical_id))
    return jsonable_encoder(await cl.track_info_by_id(track_id, max_id))


@router.get("/stream", response_model=Dict[str, Any])
async def track_stream(
    sessionid: str = Depends(get_sessionid),
    track_id: str = Query(..., alias="id"),
    max_id: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Get track stream media
    """
    cl = await clients.get(sessionid)
    return await cl.track_stream_info_by_id(track_id, max_id)


@router.get("/download/by/url")
async def track_download_by_url(
    sessionid: str = Depends(get_sessionid),
    url: str = Query(...),
    filename: Optional[str] = Query(""),
    folder: Optional[Path] = Query(""),
    returnFile: Optional[bool] = Query(True),
    clients: ClientStorage = Depends(get_clients),
):
    """Download track audio from a URL
    """
    cl = await clients.get(sessionid)
    result = await cl.track_download_by_url(url, filename, folder)
    if returnFile:
        return FileResponse(result)
    return result


@music_router.get("/feed/browser", response_model=Dict[str, Any])
async def music_feed_browser(
    sessionid: str = Depends(get_sessionid),
    browse_session_id: Optional[str] = Query(None),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Get feed music browser
    """
    cl = await clients.get(sessionid)
    return await cl.music_in_feed_audio_browser(browse_session_id)
