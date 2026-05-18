from pathlib import Path
from typing import List, Optional

from aiograpi.types import Media
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.helpers import (
    LOCATION_FORM_DESCRIPTION,
    USERTAGS_FORM_DESCRIPTION,
    album_upload_post,
    parse_upload_location,
    parse_upload_usertags,
)

router = APIRouter(
    prefix="/album",
    tags=["Album (Carousel)"],
    responses={404: {"description": "Not found"}},
)


@router.get("/download", response_model=List[Path])
async def album_download(sessionid: str = Depends(get_sessionid),
                         media_pk: int = Query(...),
                         folder: Optional[Path] = Query(""),
                         clients: ClientStorage = Depends(get_clients)) -> List[Path]:
    """Download photo using media pk
    """
    cl = await clients.get(sessionid)
    result = await cl.album_download(media_pk, folder)
    return result


@router.get("/download/by/urls", response_model=List[Path])
async def album_download_by_urls(sessionid: str = Depends(get_sessionid),
                         urls: List[str] = Query(...),
                         folder: Optional[Path] = Query(""),
                         clients: ClientStorage = Depends(get_clients)) -> List[Path]:
    """Download photo using URL
    """
    cl = await clients.get(sessionid)
    result = await cl.album_download_by_urls(urls, folder)
    return result


@router.post("/upload", response_model=Media)
async def album_upload(sessionid: str = Depends(get_sessionid),
                       files: List[UploadFile] = File(...),
                       caption: str = Form(...),
                       usertags: Optional[List[str]] = Form([], description=USERTAGS_FORM_DESCRIPTION),
                       location: Optional[str] = Form(None, description=LOCATION_FORM_DESCRIPTION),
                       clients: ClientStorage = Depends(get_clients)
                       ) -> Media:
    """Upload album to feed
    """
    cl = await clients.get(sessionid)

    return await album_upload_post(
        cl, files, caption=caption,
        usertags=parse_upload_usertags(usertags),
        location=parse_upload_location(location))
