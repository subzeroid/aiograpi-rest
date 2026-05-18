from typing import List

from aiograpi.types import Hashtag, Media
from fastapi import APIRouter, Depends, Form, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid

router = APIRouter(
    prefix="/hashtag",
    tags=["Hashtag"],
    responses={404: {"description": "Not found"}},
)


@router.get("/info", response_model=Hashtag)
async def hashtag_info(
    sessionid: str = Depends(get_sessionid),
    name: str = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> Hashtag:
    """Get hashtag info
    """
    cl = await clients.get(sessionid)
    return await cl.hashtag_info(name)


@router.get("/medias/top", response_model=List[Media])
async def hashtag_medias_top(
    sessionid: str = Depends(get_sessionid),
    name: str = Query(...),
    amount: int = Query(9),
    clients: ClientStorage = Depends(get_clients),
) -> List[Media]:
    """Get top hashtag media
    """
    cl = await clients.get(sessionid)
    return await cl.hashtag_medias_top(name, amount)


@router.get("/medias/recent", response_model=List[Media])
async def hashtag_medias_recent(
    sessionid: str = Depends(get_sessionid),
    name: str = Query(...),
    amount: int = Query(27),
    clients: ClientStorage = Depends(get_clients),
) -> List[Media]:
    """Get recent hashtag media
    """
    cl = await clients.get(sessionid)
    return await cl.hashtag_medias_recent(name, amount)


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
