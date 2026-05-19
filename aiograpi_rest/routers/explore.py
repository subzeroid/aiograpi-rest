from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid

router = APIRouter(
    prefix="/explore",
    tags=["Explore"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=Dict[str, Any])
async def explore_page(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Get Explore page
    """
    cl = await clients.get(sessionid)
    return await cl.explore_page()


@router.get("/media", response_model=Dict[str, Any])
async def explore_media(
    sessionid: str = Depends(get_sessionid),
    media_pk: int = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> Dict[str, Any]:
    """Get Explore media details
    """
    cl = await clients.get(sessionid)
    return await cl.explore_page_media_info(media_pk)
