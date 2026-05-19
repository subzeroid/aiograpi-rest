from typing import Dict, List

from aiograpi.mixins.insights import DATA_ORDERING, POST_TYPE, TIME_FRAME
from fastapi import APIRouter, Depends, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid

router = APIRouter(
    prefix="/insights",
    tags=["Insights"],
    responses={404: {"description": "Not found"}}
)


@router.get("/media/feed", response_model=List[Dict])
async def media_feed_all(sessionid: str = Depends(get_sessionid),
                         post_type: POST_TYPE = Query("ALL"),
                         time_frame: TIME_FRAME = Query("TWO_YEARS"),
                         data_ordering: DATA_ORDERING = Query("REACH_COUNT"),
                         count: int = Query(0),
                         clients: ClientStorage = Depends(get_clients)) -> List[Dict]:
    """Return medias with insights
    """
    cl = await clients.get(sessionid)
    return await cl.insights_media_feed_all(post_type, time_frame, data_ordering, count, sleep=2)


@router.get("/account", response_model=Dict)
async def account(sessionid: str = Depends(get_sessionid),
                  clients: ClientStorage = Depends(get_clients)) -> Dict:
    """Get insights for account
    """
    cl = await clients.get(sessionid)
    return await cl.insights_account()


@router.get("/media", response_model=Dict)
async def media(sessionid: str = Depends(get_sessionid),
                media_pk: int = Query(...),
                clients: ClientStorage = Depends(get_clients)) -> Dict:
    """Get insights data for media
    """
    cl = await clients.get(sessionid)
    return await cl.insights_media(media_pk)
