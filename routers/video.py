from pathlib import Path
from typing import List, Optional

import requests
from aiograpi.types import (
    Media,
)
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse

from dependencies import ClientStorage, get_clients, get_sessionid
from helpers import (
    LOCATION_FORM_DESCRIPTION,
    USERTAGS_FORM_DESCRIPTION,
    parse_upload_location,
    parse_upload_usertags,
    video_upload_post,
)

router = APIRouter(
    prefix="/video",
    tags=["Video"],
    responses={404: {"description": "Not found"}},
)


@router.get("/download")
async def video_download(sessionid: str = Depends(get_sessionid),
                         media_pk: int = Query(...),
                         folder: Optional[Path] = Query(""),
                         returnFile: Optional[bool] = Query(True),
                         clients: ClientStorage = Depends(get_clients)):
    """Download video using media pk
    """
    cl = await clients.get(sessionid)
    result = await cl.video_download(media_pk, folder)
    if returnFile:
        return FileResponse(result)
    else:
        return result


@router.get("/download/by/url")
async def video_download_by_url(sessionid: str = Depends(get_sessionid),
                         url: str = Query(...),
                         filename: Optional[str] = Query(""),
                         folder: Optional[Path] = Query(""),
                         returnFile: Optional[bool] = Query(True),
                         clients: ClientStorage = Depends(get_clients)):
    """Download video using URL
    """
    cl = await clients.get(sessionid)
    result = await cl.video_download_by_url(url, filename, folder)
    if returnFile:
        return FileResponse(result)
    else:
        return result


@router.post("/upload", response_model=Media)
async def video_upload(sessionid: str = Depends(get_sessionid),
                       file: UploadFile = File(...),
                       caption: str = Form(...),
                       thumbnail: Optional[UploadFile] = File(None),
                       usertags: Optional[List[str]] = Form([], description=USERTAGS_FORM_DESCRIPTION),
                       location: Optional[str] = Form(None, description=LOCATION_FORM_DESCRIPTION),
                       clients: ClientStorage = Depends(get_clients)
                       ) -> Media:
    """Upload photo and configure to feed
    """
    cl = await clients.get(sessionid)

    content = await file.read()
    usernames_tags = parse_upload_usertags(usertags)
    parsed_location = parse_upload_location(location)
    if thumbnail is not None:
        thumb = await thumbnail.read()
        return await video_upload_post(
            cl, content, caption=caption,
            thumbnail=thumb,
            usertags=usernames_tags,
            location=parsed_location)
    return await video_upload_post(
        cl, content, caption=caption,
        usertags=usernames_tags,
        location=parsed_location)

@router.post("/upload/by/url", response_model=Media)
async def video_upload(sessionid: str = Depends(get_sessionid),
                       url: str = Form(...),
                       caption: str = Form(...),
                       thumbnail: Optional[UploadFile] = File(None),
                       usertags: Optional[List[str]] = Form([], description=USERTAGS_FORM_DESCRIPTION),
                       location: Optional[str] = Form(None, description=LOCATION_FORM_DESCRIPTION),
                       clients: ClientStorage = Depends(get_clients)
                       ) -> Media:
    """Upload photo by URL and configure to feed
    """
    cl = await clients.get(sessionid)

    content = requests.get(url).content
    usernames_tags = parse_upload_usertags(usertags)
    parsed_location = parse_upload_location(location)
    if thumbnail is not None:
        thumb = await thumbnail.read()
        return await video_upload_post(
            cl, content, caption=caption,
            thumbnail=thumb,
            usertags=usernames_tags,
            location=parsed_location)
    return await video_upload_post(
        cl, content, caption=caption,
        usertags=usernames_tags,
        location=parsed_location)
