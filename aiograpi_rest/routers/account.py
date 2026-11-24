from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Literal, Optional

from aiograpi.exceptions import CollectionNotFound
from aiograpi.types import Account, Collection, Media, UserShort
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.pagination import MediaPage, UserShortPage

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


TimelineReason = Literal["cold_start_fetch", "warm_start_fetch", "pagination", "pull_to_refresh", "auto_refresh"]


@router.get("/feed/timeline", response_model=Dict)
async def timeline_feed(
    sessionid: str = Depends(get_sessionid),
    reason: Optional[TimelineReason] = Query(
        None,
        description=(
            "Why the feed is loaded, as the app sends it. Defaults to aiograpi's pull_to_refresh, "
            "which returns only what is new since the last load; cold_start_fetch loads the feed "
            "as on app open."
        ),
    ),
    max_id: Optional[str] = Query(
        None,
        description="next_max_id of the previous page, to load the next one (reason becomes pagination).",
    ),
    clients: ClientStorage = Depends(get_clients),
) -> Dict:
    """Get your timeline feed
    """
    cl = await clients.get(sessionid)
    kwargs: Dict[str, Any] = {}
    if reason:
        kwargs["reason"] = reason
    if max_id:
        kwargs["max_id"] = max_id
    return await cl.get_timeline_feed(**kwargs)


@router.get("/feed/new", response_model=bool)
async def account_feed_new(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Check whether the authenticated account has new feed items
    """
    cl = await clients.get(sessionid)
    return await cl.new_feed_exist()


@router.get("/feed/user/stream-item", response_model=Dict[str, Any])
async def account_feed_user_stream_item(
    sessionid: str = Depends(get_sessionid),
    item_id: str = Query(...),
    is_pull_to_refresh: bool = Query(False),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Get user feed stream item
    """
    cl = await clients.get(sessionid)
    return await cl.feed_user_stream_item(item_id, is_pull_to_refresh)


@router.get("/security", response_model=Dict[str, Any])
async def account_security(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Get authenticated account security info
    """
    cl = await clients.get(sessionid)
    return await cl.account_security_info()


@router.get("/family", response_model=Dict[str, Any])
async def account_family(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Get authenticated account family
    """
    cl = await clients.get(sessionid)
    return await cl.get_account_family_v1()


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


@router.post("/follow/requests/approve", response_model=Dict[str, bool])
async def account_follow_requests_approve(
    sessionid: str = Depends(get_sessionid),
    user_ids: List[str] = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, bool]:
    """Approve pending follow requests
    """
    cl = await clients.get(sessionid)
    return await cl.user_follow_requests_approve(user_ids)


@router.delete("/follow/requests", response_model=Dict[str, bool])
async def account_follow_requests_decline(
    sessionid: str = Depends(get_sessionid),
    user_ids: List[str] = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, bool]:
    """Decline pending follow requests
    """
    cl = await clients.get(sessionid)
    return await cl.user_follow_requests_decline(user_ids)


@router.post("/follow/request/approve", response_model=bool)
async def account_follow_request_approve(
    sessionid: str = Depends(get_sessionid),
    user_id: str = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Approve a pending follow request
    """
    cl = await clients.get(sessionid)
    return await cl.user_follow_request_approve(user_id)


@router.delete("/follow/request", response_model=bool)
async def account_follow_request_decline(
    sessionid: str = Depends(get_sessionid),
    user_id: str = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Decline a pending follow request
    """
    cl = await clients.get(sessionid)
    return await cl.user_follow_request_decline(user_id)


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


@router.get("/archive/media", response_model=MediaPage)
async def account_archive_media(
    sessionid: str = Depends(get_sessionid),
    amount: int = Query(50, ge=1, le=200),
    cursor: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> MediaPage:
    """Get a page of archived account media
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.archive_medias_paginated_v1(amount, cursor or "")
    return MediaPage(items=items, next_cursor=next_cursor or "")


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


@router.patch("/biography", response_model=bool)
async def account_biography(
    sessionid: str = Depends(get_sessionid),
    biography: str = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Update authenticated account biography
    """
    cl = await clients.get(sessionid)
    return await cl.account_set_biography(biography)


@router.patch("/external-url", response_model=Dict[str, Any])
async def account_external_url(
    sessionid: str = Depends(get_sessionid),
    external_url: str = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Update authenticated account external URL
    """
    cl = await clients.get(sessionid)
    return await cl.set_external_url(external_url)


@router.delete("/external-url", response_model=Dict[str, Any])
async def account_external_url_delete(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Clear authenticated account external URL
    """
    cl = await clients.get(sessionid)
    return await cl.set_external_url("")


@router.delete("/bio-links", response_model=Dict[str, Any])
async def account_bio_links_delete(
    sessionid: str = Depends(get_sessionid),
    link_ids: List[str] = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Remove authenticated account bio links
    """
    cl = await clients.get(sessionid)
    return await cl.remove_bio_links(link_ids)


@router.patch("/password", response_model=bool)
async def account_password(
    sessionid: str = Depends(get_sessionid),
    old_password: str = Form(...),
    new_password: str = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Change authenticated account password
    """
    cl = await clients.get(sessionid)
    result = await cl.change_password(old_password, new_password)
    if isinstance(result, dict):
        return result.get("status") == "ok"
    return bool(result)


@router.post("/password/reset", response_model=Dict[str, Any])
async def account_password_reset(
    sessionid: str = Depends(get_sessionid),
    identifier: str = Form(...),
    recaptcha_challenge_field: str = Form(""),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Request account password reset
    """
    cl = await clients.get(sessionid)
    return await cl.send_password_reset(identifier, recaptcha_challenge_field)


@router.post("/email/confirm", response_model=Dict[str, Any])
async def account_email_confirm(
    sessionid: str = Depends(get_sessionid),
    email: str = Form(...),
    code: str = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Confirm authenticated account email
    """
    cl = await clients.get(sessionid)
    return await cl.confirm_email(email, code)


@router.post("/email/confirmation", response_model=Dict[str, Any])
async def account_email_confirmation(
    sessionid: str = Depends(get_sessionid),
    email: str = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Send authenticated account email confirmation
    """
    cl = await clients.get(sessionid)
    return await cl.send_confirm_email(email)


@router.post("/phone/confirm", response_model=Dict[str, Any])
async def account_phone_confirm(
    sessionid: str = Depends(get_sessionid),
    phone_number: str = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Send account phone confirmation
    """
    cl = await clients.get(sessionid)
    return await cl.send_confirm_phone_number(phone_number)


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
