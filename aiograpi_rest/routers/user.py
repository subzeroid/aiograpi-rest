import json
from typing import Any, Dict, List, Optional

from aiograpi.extractors import json_value
from aiograpi.types import About, Highlight, Relationship, User, UserShort
from fastapi import APIRouter, Depends, Form, HTTPException, Query
from pydantic import ValidationError

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.pagination import UserShortPage

router = APIRouter(
    prefix="/user",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)


def _normalize_about(value: Any) -> About:
    if isinstance(value, dict):
        payload = dict(value)
    else:
        payload = value.model_dump()

    for field in ("username", "country", "date", "former_usernames"):
        field_value = payload.get(field)
        if isinstance(field_value, bool):
            payload[field] = ""
        elif field_value is not None and not isinstance(field_value, str):
            payload[field] = str(field_value)

    return About(**payload)


def _extract_about_from_last_json(data: Dict) -> About:
    payload = {}
    content = json_value(data, "layout", "bloks_payload", "data", 0, "data")
    if isinstance(content, dict):
        payload["country"] = content.get("initial")

    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
    payload["is_verified"] = '"Verified"' in serialized
    date_found = False
    parts = serialized.split('")":')
    for index, value in enumerate(parts):
        if '"bold"}' in value:
            payload["username"] = value.strip().split(",")[0][1:-1]
        if date_found:
            payload["date"] = value.strip().split(",")[0][1:-1]
        if "Former usernames" in value:
            payload["former_usernames"] = parts[index + 2].strip().split(",")[0][1:-1]
        date_found = '"Date joined"' in value
    return _normalize_about(payload)


@router.get("/followers", response_model=UserShortPage)
async def user_followers(sessionid: str = Depends(get_sessionid),
                         user_id: str = Query(...),
                         amount: int = Query(50, ge=1, le=200),
                         cursor: str = Query(""),
                         clients: ClientStorage = Depends(get_clients)) -> UserShortPage:
    """Get a page of user's followers
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.user_followers_v1_chunk(user_id, amount, cursor or "")
    return UserShortPage(items=items, next_cursor=next_cursor or "")


@router.get("/following", response_model=UserShortPage)
async def user_following(sessionid: str = Depends(get_sessionid),
                         user_id: str = Query(...),
                         amount: int = Query(50, ge=1, le=200),
                         cursor: str = Query(""),
                         clients: ClientStorage = Depends(get_clients)) -> UserShortPage:
    """Get a page of user's following
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.user_following_v1_chunk(user_id, amount, cursor or "")
    return UserShortPage(items=items, next_cursor=next_cursor or "")


@router.get("", response_model=User)
async def user(sessionid: str = Depends(get_sessionid),
               user_id: Optional[str] = Query(None),
               username: Optional[str] = Query(None),
               use_cache: Optional[bool] = Query(True),
               clients: ClientStorage = Depends(get_clients)) -> User:
    """Get user profile by user id or username
    """
    if user_id and username:
        raise HTTPException(status_code=422, detail="Provide either user_id or username, not both")
    if not user_id and not username:
        raise HTTPException(status_code=422, detail="Provide user_id or username")

    cl = await clients.get(sessionid)
    if username:
        return await cl.user_info_by_username(username.strip().lstrip("@"))
    return await cl.user_info(user_id.strip())


@router.get("/about", response_model=About)
async def user_about(sessionid: str = Depends(get_sessionid),
                     user_id: str = Query(...),
                     clients: ClientStorage = Depends(get_clients)) -> About:
    """Get user about details (verification, country, join date)
    """
    cl = await clients.get(sessionid)
    try:
        about = await cl.user_about_v1(user_id)
    except ValidationError:
        last_json = getattr(cl, "last_json", None)
        if not last_json:
            raise
        return _extract_about_from_last_json(last_json)
    return _normalize_about(about)


@router.post("/follow", response_model=bool)
async def user_follow(sessionid: str = Depends(get_sessionid),
                      user_id: int = Form(...),
                      clients: ClientStorage = Depends(get_clients)) -> bool:
    """Follow a user
    """
    cl = await clients.get(sessionid)
    return await cl.user_follow(user_id)


@router.delete("/follow", response_model=bool)
async def user_unfollow(sessionid: str = Depends(get_sessionid),
                        user_id: int = Query(...),
                        clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unfollow a user
    """
    cl = await clients.get(sessionid)
    return await cl.user_unfollow(user_id)


@router.delete("/follower", response_model=bool)
async def user_remove_follower(sessionid: str = Depends(get_sessionid),
                               user_id: int = Query(...),
                               clients: ClientStorage = Depends(get_clients)) -> bool:
    """Remove a follower
    """
    cl = await clients.get(sessionid)
    return await cl.user_remove_follower(user_id)


@router.post("/mute/posts", response_model=bool)
async def mute_posts_from_follow(sessionid: str = Depends(get_sessionid),
                                 user_id: int = Form(...),
                                 revert: Optional[bool] = Form(False),
                                 clients: ClientStorage = Depends(get_clients)) -> bool:
    """Mute posts from following user
    """
    cl = await clients.get(sessionid)
    return await cl.mute_posts_from_follow(user_id, revert)


@router.delete("/mute/posts", response_model=bool)
async def unmute_posts_from_follow(sessionid: str = Depends(get_sessionid),
                                   user_id: int = Query(...),
                                   clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unmute posts from following user
    """
    cl = await clients.get(sessionid)
    return await cl.unmute_posts_from_follow(user_id)


@router.post("/mute/stories", response_model=bool)
async def mute_stories_from_follow(sessionid: str = Depends(get_sessionid),
                                   user_id: int = Form(...),
                                   revert: Optional[bool] = Form(False),
                                   clients: ClientStorage = Depends(get_clients)) -> bool:
    """Mute stories from following user
    """
    cl = await clients.get(sessionid)
    return await cl.mute_stories_from_follow(user_id, revert)


@router.delete("/mute/stories", response_model=bool)
async def unmute_stories_from_follow(sessionid: str = Depends(get_sessionid),
                                     user_id: int = Query(...),
                                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unmute stories from following user
    """
    cl = await clients.get(sessionid)
    return await cl.unmute_stories_from_follow(user_id)


@router.get("/friendship", response_model=Relationship)
async def user_friendship(sessionid: str = Depends(get_sessionid),
                          user_id: str = Query(...),
                          clients: ClientStorage = Depends(get_clients)) -> Relationship:
    """Get relationship with a user
    """
    cl = await clients.get(sessionid)
    return await cl.user_friendship_v1(user_id)


@router.post("/block", response_model=bool)
async def user_block(sessionid: str = Depends(get_sessionid),
                     user_id: str = Form(...),
                     surface: Optional[str] = Form("profile"),
                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Block a user
    """
    cl = await clients.get(sessionid)
    return await cl.user_block(user_id, surface)


@router.delete("/block", response_model=bool)
async def user_unblock(sessionid: str = Depends(get_sessionid),
                       user_id: str = Query(...),
                       surface: Optional[str] = Query("profile"),
                       clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unblock a user
    """
    cl = await clients.get(sessionid)
    return await cl.user_unblock(user_id, surface)


@router.get("/highlights", response_model=List[Highlight])
async def user_highlights(sessionid: str = Depends(get_sessionid),
                          user_id: int = Query(...),
                          amount: Optional[int] = Query(0),
                          clients: ClientStorage = Depends(get_clients)) -> List[Highlight]:
    """Get user highlights
    """
    cl = await clients.get(sessionid)
    return await cl.user_highlights(user_id, amount)
