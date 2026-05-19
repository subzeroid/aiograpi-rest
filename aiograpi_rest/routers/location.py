from typing import List

from aiograpi.types import Guide, Location
from fastapi import APIRouter, Depends, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.pagination import MediaPage

router = APIRouter(
    prefix="/location",
    tags=["Location"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=Location)
async def location(
    sessionid: str = Depends(get_sessionid),
    location_pk: int = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> Location:
    """Get location info
    """
    cl = await clients.get(sessionid)
    return await cl.location_info(location_pk)


@router.get("/media/top", response_model=MediaPage)
async def location_medias_top(
    sessionid: str = Depends(get_sessionid),
    location_pk: int = Query(...),
    amount: int = Query(27, ge=1, le=200),
    cursor: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> MediaPage:
    """Get a page of top location media
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.location_medias_v1_chunk(location_pk, amount, "ranked", cursor or None)
    return MediaPage(items=items, next_cursor=next_cursor or "")


@router.get("/media/recent", response_model=MediaPage)
async def location_medias_recent(
    sessionid: str = Depends(get_sessionid),
    location_pk: int = Query(...),
    amount: int = Query(63, ge=1, le=200),
    cursor: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> MediaPage:
    """Get a page of recent location media
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.location_medias_v1_chunk(location_pk, amount, "recent", cursor or None)
    return MediaPage(items=items, next_cursor=next_cursor or "")


@router.get("/guides", response_model=List[Guide])
async def location_guides(
    sessionid: str = Depends(get_sessionid),
    location_pk: int = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> List[Guide]:
    """Get location guides
    """
    cl = await clients.get(sessionid)
    return await cl.location_guides_v1(location_pk)
