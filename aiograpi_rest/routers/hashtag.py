from typing import List

from aiograpi.types import Hashtag, Media
from fastapi import APIRouter, Depends, Form, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.pagination import MediaPage

router = APIRouter(
    prefix="/hashtag",
    tags=["Hashtag"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=Hashtag)
async def hashtag(
    sessionid: str = Depends(get_sessionid),
    name: str = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> Hashtag:
    """Get hashtag info
    """
    cl = await clients.get(sessionid)
    return await cl.hashtag_info(name)


@router.get("/media/top", response_model=MediaPage)
async def hashtag_medias_top(
    sessionid: str = Depends(get_sessionid),
    name: str = Query(...),
    amount: int = Query(9, ge=1, le=200),
    cursor: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> MediaPage:
    """Get a page of top hashtag media
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.hashtag_medias_v1_chunk(name, amount, "top", cursor or None)
    return MediaPage(items=items, next_cursor=next_cursor or "")


@router.get("/media/recent", response_model=MediaPage)
async def hashtag_medias_recent(
    sessionid: str = Depends(get_sessionid),
    name: str = Query(...),
    amount: int = Query(27, ge=1, le=200),
    cursor: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> MediaPage:
    """Get a page of recent hashtag media
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.hashtag_medias_v1_chunk(name, amount, "recent", cursor or None)
    return MediaPage(items=items, next_cursor=next_cursor or "")


@router.get("/related", response_model=List[Hashtag])
async def hashtag_related(
    sessionid: str = Depends(get_sessionid),
    name: str = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> List[Hashtag]:
    """Get related hashtags
    """
    cl = await clients.get(sessionid)
    return await cl.hashtag_related_hashtags(name)


@router.get("/reels", response_model=List[Media])
async def hashtag_reels(
    sessionid: str = Depends(get_sessionid),
    name: str = Query(...),
    amount: int = Query(27, ge=1, le=200),
    clients: ClientStorage = Depends(get_clients),
) -> List[Media]:
    """Get hashtag Reels
    """
    cl = await clients.get(sessionid)
    return await cl.hashtag_medias_reels_v1(name, amount)


@router.post("/follow", response_model=bool)
async def hashtag_follow(
    sessionid: str = Depends(get_sessionid),
    hashtag: str = Form(...),
    unfollow: bool = Form(False),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Follow a hashtag
    """
    cl = await clients.get(sessionid)
    return await cl.hashtag_follow(hashtag, unfollow)


@router.delete("/follow", response_model=bool)
async def hashtag_unfollow(
    sessionid: str = Depends(get_sessionid),
    hashtag: str = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Unfollow a hashtag
    """
    cl = await clients.get(sessionid)
    return await cl.hashtag_unfollow(hashtag)
