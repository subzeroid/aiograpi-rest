from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from aiograpi.exceptions import CollectionNotFound
from aiograpi.types import Account, Collection, Media, UserShort
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.pagination import UserShortPage

router = APIRouter(
    prefix="/account",
    tags=["Account"],
    responses={404: {"description": "Not found"}},
)


def _collection_value(collection: Collection | dict[str, Any], key: str) -> Any:
    if isinstance(collection, dict):
        return collection.get(key)
    return getattr(collection, key)


def _ensure_single_collection_selector(collection_pk: Optional[str], name: Optional[str]) -> None:
    if not collection_pk and not name:
        raise HTTPException(status_code=422, detail="Provide collection_pk or name")
    if collection_pk and name:
        raise HTTPException(status_code=422, detail="Provide only one of collection_pk or name")


async def _get_collection_by_selector(cl: Any, collection_pk: Optional[str], name: Optional[str]) -> Collection:
    _ensure_single_collection_selector(collection_pk, name)
    if name:
        try:
            collection_pk = str(await cl.collection_pk_by_name(name))
        except CollectionNotFound as exc:
            raise HTTPException(status_code=404, detail="Collection not found") from exc

    for collection in await cl.collections():
        if str(_collection_value(collection, "id")) == str(collection_pk):
            return collection
    raise HTTPException(status_code=404, detail="Collection not found")


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


@router.get("/collections", response_model=List[Collection])
async def account_collections(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> List[Collection]:
    """List saved collections
    """
    cl = await clients.get(sessionid)
    return await cl.collections()


@router.get("/collection", response_model=Collection)
async def account_collection(
    sessionid: str = Depends(get_sessionid),
    collection_pk: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    clients: ClientStorage = Depends(get_clients),
) -> Collection:
    """Get a saved collection by collection PK or name
    """
    cl = await clients.get(sessionid)
    return await _get_collection_by_selector(cl, collection_pk, name)


@router.get("/collection/media", response_model=List[Media])
async def account_collection_media(
    sessionid: str = Depends(get_sessionid),
    collection_pk: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    amount: int = Query(21, ge=1, le=200),
    last_media_pk: int = Query(0, ge=0),
    clients: ClientStorage = Depends(get_clients),
) -> List[Media]:
    """List media in a saved collection
    """
    _ensure_single_collection_selector(collection_pk, name)
    cl = await clients.get(sessionid)
    if name:
        return await cl.collection_medias_by_name(name)
    return await cl.collection_medias(collection_pk, amount, last_media_pk)


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
