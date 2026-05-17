from typing import Dict, List, Optional

from aiograpi import Client
from aiograpi.types import Comment, Location, Media, UserShort, Usertag
from fastapi import APIRouter, Depends, Form, Query
from pydantic import BaseModel

from dependencies import ClientStorage, get_clients, get_sessionid

router = APIRouter(
    prefix="/media",
    tags=["Media"],
    responses={404: {"description": "Not found"}}
)


class MediaPage(BaseModel):
    items: List[Media]
    end_cursor: str


@router.get("/id")
async def media_id(media_pk: int) -> str:
    """Get full media id
    """
    return await Client().media_id(media_pk)


@router.get("/pk")
async def media_pk(media_id: str) -> str:
    """Get short media id
    """
    return str(Client().media_pk(media_id))


@router.get("/pk/from/code")
async def media_pk_from_code(code: str) -> str:
    """Get media pk from code
    """
    return str(Client().media_pk_from_code(code))


@router.get("/pk/from/url")
async def media_pk_from_url(url: str) -> str:
    """Get Media PK from URL
    """
    return str(await Client().media_pk_from_url(url))


@router.get("/info", response_model=Media)
async def media_info(sessionid: str = Depends(get_sessionid),
                     pk: int = Query(...),
                     use_cache: Optional[bool] = Query(True),
                     clients: ClientStorage = Depends(get_clients)) -> Media:
    """Get media info by pk
    """
    cl = await clients.get(sessionid)
    return await cl.media_info(pk, use_cache)


@router.get("/user/medias", response_model=MediaPage)
async def user_medias(sessionid: str = Depends(get_sessionid),
                      user_id: str = Query(...),
                      amount: Optional[int] = Query(50),
                      end_cursor: Optional[str] = Query(""),
                      clients: ClientStorage = Depends(get_clients)) -> MediaPage:
    """Get a user's media page with the next pagination cursor
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.user_medias_paginated(user_id, amount, end_cursor or "")
    return MediaPage(items=items, end_cursor=next_cursor or "")


@router.get("/usertag/medias", response_model=List[Media])
async def usertag_medias(sessionid: str = Depends(get_sessionid),
                         user_id: int = Query(...),
                         amount: Optional[int] = Query(50),
                         clients: ClientStorage = Depends(get_clients)) -> List[Media]:
    """Get medias where a user is tagged
    """
    cl = await clients.get(sessionid)
    return await cl.usertag_medias(user_id, amount)


@router.delete("", response_model=bool)
async def media_delete(sessionid: str = Depends(get_sessionid),
                       media_id: str = Query(...),
                       clients: ClientStorage = Depends(get_clients)) -> bool:
    """Delete media by Media ID
    """
    cl = await clients.get(sessionid)
    return await cl.media_delete(media_id)


@router.patch("", response_model=Dict)
async def media_edit(sessionid: str = Depends(get_sessionid),
                     media_id: str = Form(...),
                     caption: str = Form(...),
                     title: Optional[str] = Form(""),
                     usertags: Optional[List[Usertag]] = Form([]),
                     location: Optional[Location] = Form(None),
                     clients: ClientStorage = Depends(get_clients)) -> Dict:
    """Edit caption for media
    """
    cl = await clients.get(sessionid)
    return await cl.media_edit(media_id, caption, title, usertags, location)


@router.get("/user", response_model=UserShort)
async def media_user(sessionid: str = Depends(get_sessionid),
                     media_pk: int = Query(...),
                     clients: ClientStorage = Depends(get_clients)) -> UserShort:
    """Get author of the media
    """
    cl = await clients.get(sessionid)
    return await cl.media_user(media_pk)


@router.get("/oembed", response_model=Dict)
async def media_oembed(sessionid: str = Depends(get_sessionid),
                     url: str = Query(...),
                     clients: ClientStorage = Depends(get_clients)) -> Dict:
    """Return info about media and user from post URL
    """
    cl = await clients.get(sessionid)
    return await cl.media_oembed(url)


@router.post("/like", response_model=bool)
async def media_like(sessionid: str = Depends(get_sessionid),
                     media_id: str = Form(...),
                     revert: Optional[bool] = Form(False),
                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Like a media
    """
    cl = await clients.get(sessionid)
    return await cl.media_like(media_id, revert)


@router.delete("/like", response_model=bool)
async def media_unlike(sessionid: str = Depends(get_sessionid),
                       media_id: str = Query(...),
                       clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unlike a media
    """
    cl = await clients.get(sessionid)
    return await cl.media_unlike(media_id)


@router.patch("/seen", response_model=bool)
async def media_seen(sessionid: str = Depends(get_sessionid),
                     media_ids: List[str] = Form(...),
                     skipped_media_ids: Optional[List[str]] = Form([]),
                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Mark a media as seen
    """
    cl = await clients.get(sessionid)
    return await cl.media_seen(media_ids, skipped_media_ids)


@router.get("/likers", response_model=List[UserShort])
async def media_likers(sessionid: str = Depends(get_sessionid),
                     media_id: str = Query(...),
                     clients: ClientStorage = Depends(get_clients)) -> List[UserShort]:
    """Get user's likers
    """
    cl = await clients.get(sessionid)
    return await cl.media_likers(media_id)


@router.post("/archive", response_model=bool)
async def media_archive(sessionid: str = Depends(get_sessionid),
                     media_id: str = Form(...),
                     revert: Optional[bool] = Form(False),
                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Archive a media
    """
    cl = await clients.get(sessionid)
    return await cl.media_archive(media_id, revert)


@router.delete("/archive", response_model=bool)
async def media_unarchive(sessionid: str = Depends(get_sessionid),
                     media_id: str = Query(...),
                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unarchive a media
    """
    cl = await clients.get(sessionid)
    return await cl.media_unarchive(media_id)


@router.get("/comments", response_model=List[Comment])
async def media_comments(sessionid: str = Depends(get_sessionid),
                         media_id: str = Query(...),
                         amount: Optional[int] = Query(20),
                         clients: ClientStorage = Depends(get_clients)) -> List[Comment]:
    """Get media comments
    """
    cl = await clients.get(sessionid)
    return await cl.media_comments(media_id, amount)


@router.post("/comment", response_model=Comment)
async def media_comment(sessionid: str = Depends(get_sessionid),
                        media_id: str = Form(...),
                        text: str = Form(...),
                        replied_to_comment_id: Optional[int] = Form(None),
                        clients: ClientStorage = Depends(get_clients)) -> Comment:
    """Create a media comment
    """
    cl = await clients.get(sessionid)
    return await cl.media_comment(media_id, text, replied_to_comment_id)


@router.delete("/comment", response_model=bool)
async def media_comment_delete(sessionid: str = Depends(get_sessionid),
                               media_id: str = Query(...),
                               comment_pk: int = Query(...),
                               clients: ClientStorage = Depends(get_clients)) -> bool:
    """Delete a media comment
    """
    cl = await clients.get(sessionid)
    return await cl.comment_bulk_delete(media_id, [comment_pk])


@router.get("/comment/replies", response_model=List[Comment])
async def media_comment_replies(sessionid: str = Depends(get_sessionid),
                                media_id: str = Query(...),
                                comment_id: str = Query(...),
                                amount: Optional[int] = Query(0),
                                clients: ClientStorage = Depends(get_clients)) -> List[Comment]:
    """Get media comment replies
    """
    cl = await clients.get(sessionid)
    return await cl.media_comment_replies(media_id, comment_id, amount)


@router.post("/comment/like", response_model=bool)
async def media_comment_like(sessionid: str = Depends(get_sessionid),
                             comment_pk: int = Form(...),
                             revert: Optional[bool] = Form(False),
                             clients: ClientStorage = Depends(get_clients)) -> bool:
    """Like a media comment
    """
    cl = await clients.get(sessionid)
    return await cl.comment_like(comment_pk, revert)


@router.delete("/comment/like", response_model=bool)
async def media_comment_unlike(sessionid: str = Depends(get_sessionid),
                               comment_pk: int = Query(...),
                               clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unlike a media comment
    """
    cl = await clients.get(sessionid)
    return await cl.comment_unlike(comment_pk)


@router.get("/liked", response_model=List[Media])
async def liked_medias(sessionid: str = Depends(get_sessionid),
                       amount: Optional[int] = Query(21),
                       last_media_pk: Optional[int] = Query(0),
                       clients: ClientStorage = Depends(get_clients)) -> List[Media]:
    """Get liked media
    """
    cl = await clients.get(sessionid)
    return await cl.liked_medias(amount, last_media_pk)


@router.post("/save", response_model=bool)
async def media_save(sessionid: str = Depends(get_sessionid),
                     media_id: str = Form(...),
                     collection_pk: Optional[int] = Form(None),
                     revert: Optional[bool] = Form(False),
                     clients: ClientStorage = Depends(get_clients)) -> bool:
    """Save media
    """
    cl = await clients.get(sessionid)
    return await cl.media_save(media_id, collection_pk, revert)


@router.delete("/save", response_model=bool)
async def media_unsave(sessionid: str = Depends(get_sessionid),
                       media_id: str = Query(...),
                       collection_pk: Optional[int] = Query(None),
                       clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unsave media
    """
    cl = await clients.get(sessionid)
    return await cl.media_unsave(media_id, collection_pk)


@router.post("/pin", response_model=bool)
async def media_pin(sessionid: str = Depends(get_sessionid),
                    media_pk: str = Form(...),
                    revert: Optional[bool] = Form(False),
                    clients: ClientStorage = Depends(get_clients)) -> bool:
    """Pin media
    """
    cl = await clients.get(sessionid)
    return await cl.media_pin(media_pk, revert)


@router.delete("/pin", response_model=bool)
async def media_unpin(sessionid: str = Depends(get_sessionid),
                      media_pk: str = Query(...),
                      clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unpin media
    """
    cl = await clients.get(sessionid)
    return await cl.media_unpin(media_pk)
