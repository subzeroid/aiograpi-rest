from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from aiograpi.types import Account, UserShort
from fastapi import APIRouter, Depends, File, Form, UploadFile

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid

router = APIRouter(
    prefix="/account",
    tags=["Account"],
    responses={404: {"description": "Not found"}},
)


@router.get("/info", response_model=Account)
async def account_info(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> Account:
    """Get authenticated account info
    """
    cl = await clients.get(sessionid)
    return await cl.account_info()


@router.patch("/profile", response_model=Account)
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
