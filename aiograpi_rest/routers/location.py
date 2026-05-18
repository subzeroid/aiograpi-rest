from typing import List, Optional

from aiograpi.types import Location
from fastapi import APIRouter, Depends, HTTPException, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.pagination import MediaPage

router = APIRouter(
    prefix="/location",
    tags=["Location"],
    responses={404: {"description": "Not found"}},
)


@router.get("/search", response_model=List[Location])
async def location_search(
    sessionid: str = Depends(get_sessionid),
    name: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    clients: ClientStorage = Depends(get_clients),
) -> List[Location]:
    """Search locations by name or coordinates
    """
    cl = await clients.get(sessionid)
    if name:
        return await cl.location_search_name(name)
    if lat is None or lng is None:
        raise HTTPException(status_code=422, detail="Provide name or both lat and lng")
    return await cl.location_search(lat, lng)


@router.get("/info", response_model=Location)
async def location_info(
    sessionid: str = Depends(get_sessionid),
    location_pk: int = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> Location:
    """Get location info
    """
    cl = await clients.get(sessionid)
    return await cl.location_info(location_pk)


@router.get("/medias/top", response_model=MediaPage)
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


@router.get("/medias/recent", response_model=MediaPage)
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
