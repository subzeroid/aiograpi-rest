from pathlib import Path
from typing import List, Optional

import requests
from aiograpi.types import (
    Media,
)
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import AnyHttpUrl

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.helpers import (
    LOCATION_FORM_DESCRIPTION,
    USERTAGS_FORM_DESCRIPTION,
    parse_upload_location,
    parse_upload_usertags,
    photo_upload_post,
)

router = APIRouter(
    prefix="/photo",
    tags=["Photo"],
    responses={404: {"description": "Not found"}},
)


@router.get("/download")
async def photo_download(sessionid: str = Depends(get_sessionid),
                         media_pk: int = Query(...),
                         folder: Optional[Path] = Query(""),
                         returnFile: Optional[bool] = Query(True),
                         clients: ClientStorage = Depends(get_clients)):
    """Download photo using media pk
    """
    cl = await clients.get(sessionid)
    result = await cl.photo_download(media_pk, folder)
    if returnFile:
        return FileResponse(result)
    else:
        return result


@router.get("/download/by/url")
async def photo_download_by_url(sessionid: str = Depends(get_sessionid),
                         url: str = Query(...),
                         filename: Optional[str] = Query(""),
                         folder: Optional[Path] = Query(""),
                         returnFile: Optional[bool] = Query(True),
                         clients: ClientStorage = Depends(get_clients)):
    """Download photo using URL
    """
    cl = await clients.get(sessionid)
    result = await cl.photo_download_by_url(url, filename, folder)
    if returnFile:
        return FileResponse(result)
    else:
        return result


@router.post("/upload", response_model=Media)
async def photo_upload(sessionid: str = Depends(get_sessionid),
                       file: UploadFile = File(...),
                       caption: str = Form(...),
                       upload_id: Optional[str] = Form(""),
                       usertags: Optional[List[str]] = Form([], description=USERTAGS_FORM_DESCRIPTION),
                       location: Optional[str] = Form(None, description=LOCATION_FORM_DESCRIPTION),
                       clients: ClientStorage = Depends(get_clients)
                       ) -> Media:
    """Upload photo and configure to feed
    """
    cl = await clients.get(sessionid)

    content = await file.read()
    return await photo_upload_post(
        cl, content, caption=caption,
        upload_id=upload_id,
        usertags=parse_upload_usertags(usertags),
        location=parse_upload_location(location))

@router.post("/upload/by/url", response_model=Media)
async def photo_upload(sessionid: str = Depends(get_sessionid),
                       url: AnyHttpUrl = Form(...),
                       caption: str = Form(...),
                       upload_id: Optional[str] = Form(""),
                       usertags: Optional[List[str]] = Form([], description=USERTAGS_FORM_DESCRIPTION),
                       location: Optional[str] = Form(None, description=LOCATION_FORM_DESCRIPTION),
                       clients: ClientStorage = Depends(get_clients)
                       ) -> Media:
    """Upload photo and configure to feed
    """
    cl = await clients.get(sessionid)

    content = requests.get(url).content
    return await photo_upload_post(
        cl, content, caption=caption,
        upload_id=upload_id,
        usertags=parse_upload_usertags(usertags),
        location=parse_upload_location(location))
