from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List, Optional

from aiograpi.types import Account, Media, UserShort
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.pagination import UserShortPage

router = APIRouter(
    prefix="/account",
    tags=["Account"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=Account)
async def account_info(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> Account:
    """Get authenticated account info
    """
    cl = await clients.get(sessionid)
    return await cl.account_info()


@router.get("/feed/timeline", response_model=Dict)
async def timeline_feed(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> Dict:
    """Get your timeline feed
    """
    cl = await clients.get(sessionid)
    return await cl.get_timeline_feed()


@router.get("/follow/requests", response_model=UserShortPage)
async def account_follow_requests(
    sessionid: str = Depends(get_sessionid),
    amount: int = Query(50, ge=1, le=200),
    cursor: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> UserShortPage:
    """Get a page of pending follow requests for the authenticated account
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.user_follow_requests_chunk(amount, cursor or "")
    return UserShortPage(items=items, next_cursor=next_cursor or "")


@router.get("/liked/media", response_model=List[Media])
async def liked_medias(
    sessionid: str = Depends(get_sessionid),
    amount: Optional[int] = Query(21),
    last_media_pk: Optional[int] = Query(0),
    clients: ClientStorage = Depends(get_clients),
) -> List[Media]:
    """Get media liked by the authenticated account
    """
    cl = await clients.get(sessionid)
    return await cl.liked_medias(amount, last_media_pk)


@router.patch("", response_model=Account)
async def account_profile(
    sessionid: str = Depends(get_sessionid),
    external_url: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    biography: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    clients: ClientStorage = Depends(get_clients),
) -> Account:
    """Update authenticated account profile fields
    """
    cl = await clients.get(sessionid)
    data = {
        key: value
        for key, value in {
            "external_url": external_url,
            "username": username,
            "full_name": full_name,
            "biography": biography,
            "phone_number": phone_number,
            "email": email,
        }.items()
        if value is not None
    }
    return await cl.account_edit(**data)


@router.patch("/picture", response_model=UserShort)
async def account_picture(
    sessionid: str = Depends(get_sessionid),
    picture: UploadFile = File(...),
    clients: ClientStorage = Depends(get_clients),
) -> UserShort:
    """Update authenticated account profile picture
    """
    cl = await clients.get(sessionid)
    suffix = Path(picture.filename or "").suffix or ".jpg"
    tmp_path = None
    try:
        with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await picture.read())
            tmp_path = Path(tmp.name)
        return await cl.account_change_picture(tmp_path)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


@router.patch("/privacy", response_model=bool)
async def account_privacy(
    sessionid: str = Depends(get_sessionid),
    is_private: bool = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Set authenticated account privacy
    """
    cl = await clients.get(sessionid)
    if is_private:
        return await cl.account_set_private()
    return await cl.account_set_public()
