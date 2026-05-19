from typing import List

from aiograpi.types import Media
from fastapi import APIRouter, Depends, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid

router = APIRouter(
    prefix="/reels",
    tags=["Reels"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=List[Media])
async def reels(
    sessionid: str = Depends(get_sessionid),
    amount: int = Query(10, ge=1, le=200),
    last_media_pk: int = Query(0, ge=0),
    clients: ClientStorage = Depends(get_clients),
) -> List[Media]:
    """List connected Reels
    """
    cl = await clients.get(sessionid)
    return await cl.reels(amount, last_media_pk)


@router.get("/friends", response_model=List[Media])
async def reels_friends(
    sessionid: str = Depends(get_sessionid),
    amount: int = Query(10, ge=1, le=200),
    last_media_pk: int = Query(0, ge=0),
    clients: ClientStorage = Depends(get_clients),
) -> List[Media]:
    """List friends Reels
    """
    cl = await clients.get(sessionid)
    return await cl.friends_reels(amount, last_media_pk)


@router.get("/explore", response_model=List[Media])
async def reels_explore(
    sessionid: str = Depends(get_sessionid),
    amount: int = Query(10, ge=1, le=200),
    last_media_pk: int = Query(0, ge=0),
    clients: ClientStorage = Depends(get_clients),
) -> List[Media]:
    """List explore Reels
    """
    cl = await clients.get(sessionid)
    return await cl.explore_reels(amount, last_media_pk)


@router.get("/timeline", response_model=List[Media])
async def reels_timeline(
    sessionid: str = Depends(get_sessionid),
    collection_pk: str = Query(...),
    amount: int = Query(10, ge=1, le=200),
    last_media_pk: int = Query(0, ge=0),
    clients: ClientStorage = Depends(get_clients),
) -> List[Media]:
    """List Reels timeline media
    """
    cl = await clients.get(sessionid)
    return await cl.reels_timeline_media(collection_pk, amount, last_media_pk)
