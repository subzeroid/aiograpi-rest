from typing import Any, Dict, List, Optional

from aiograpi import Client
from aiograpi.types import Comment, Media, UserShort
from fastapi import APIRouter, Depends, Form, HTTPException, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.helpers import (
    LOCATION_FORM_DESCRIPTION,
    USERTAGS_FORM_DESCRIPTION,
    parse_upload_location,
    parse_upload_usertags,
)
from aiograpi_rest.pagination import CommentPage, CommentStreamPage, MediaPage

router = APIRouter(
    prefix="/media",
    tags=["Media (Post)"],
    responses={404: {"description": "Not found"}}
)
user_router = APIRouter(
    prefix="/user",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)


@router.get("", response_model=Media)
async def media_info(sessionid: str = Depends(get_sessionid),
                     pk: Optional[int] = Query(None),
                     media_id: Optional[str] = Query(None, alias="id"),
                     code: Optional[str] = Query(None),
                     url: Optional[str] = Query(None),
                     use_cache: Optional[bool] = Query(True),
                     clients: ClientStorage = Depends(get_clients)) -> Media:
    """Get media info by pk, media id, shortcode, or URL
    """
    identifiers = [value is not None for value in (pk, media_id, code, url)]
    if identifiers.count(True) != 1:
        raise HTTPException(status_code=422, detail="Provide exactly one of pk, id, code, or url")

    media_pk = pk
    if media_id is not None:
        media_pk = Client().media_pk(media_id)
    elif code is not None:
        media_pk = Client().media_pk_from_code(code)
    elif url is not None:
        media_pk = await Client().media_pk_from_url(url)

    cl = await clients.get(sessionid)
    return await cl.media_info(int(media_pk), use_cache)


async def _resolve_user_id(cl, user_id: Optional[str], username: Optional[str]) -> str:
    if user_id and username:
        raise HTTPException(status_code=422, detail="Provide either user_id or username, not both")
    if username:
        user = await cl.user_info_by_username_v1(username.strip().lstrip("@"))
        return str(user.pk)
    if not user_id:
        raise HTTPException(status_code=422, detail="Provide user_id or username")

    user_id = user_id.strip()
    if user_id.isdecimal():
        return user_id
    user = await cl.user_info_by_username_v1(user_id.lstrip("@"))
    return str(user.pk)


async def _user_medias_page(cl,
                            user_id: Optional[str],
                            username: Optional[str],
                            amount: int,
                            cursor: str) -> MediaPage:
    user_id = await _resolve_user_id(cl, user_id, username)
    items, next_cursor = await cl.user_medias_paginated_v1(user_id, amount, cursor or "")
    return MediaPage(items=items, next_cursor=next_cursor or "")


async def _user_tagged_medias_page(cl,
                                   user_id: Optional[str],
                                   username: Optional[str],
                                   amount: int,
                                   cursor: str) -> MediaPage:
    user_id = await _resolve_user_id(cl, user_id, username)
    items, next_cursor = await cl.usertag_medias_paginated(user_id, amount, cursor or "")
    return MediaPage(items=items, next_cursor=next_cursor or "")


async def _user_clips_page(cl,
                           user_id: Optional[str],
                           username: Optional[str],
                           amount: int,
                           cursor: str) -> MediaPage:
    user_id = await _resolve_user_id(cl, user_id, username)
    items, next_cursor = await cl.user_clips_paginated_v1(user_id, amount, cursor or "")
    return MediaPage(items=items, next_cursor=next_cursor or "")


async def _user_videos_page(cl,
                            user_id: Optional[str],
                            username: Optional[str],
                            amount: int,
                            cursor: str) -> MediaPage:
    user_id = await _resolve_user_id(cl, user_id, username)
    items, next_cursor = await cl.user_videos_paginated_v1(user_id, amount, cursor or "")
    return MediaPage(items=items, next_cursor=next_cursor or "")


@user_router.get("/posts", response_model=MediaPage)
async def user_medias(sessionid: str = Depends(get_sessionid),
                      user_id: Optional[str] = Query(None, description="Instagram numeric user PK."),
                      username: Optional[str] = Query(None, description="Instagram username."),
                      amount: int = Query(50, ge=1, le=200),
                      cursor: str = Query(""),
                      clients: ClientStorage = Depends(get_clients)) -> MediaPage:
    """Get a user's media page with the next pagination cursor
    """
    cl = await clients.get(sessionid)
    return await _user_medias_page(cl, user_id, username, amount, cursor)


@user_router.get("/tagged/posts", response_model=MediaPage)
async def user_tagged_medias(sessionid: str = Depends(get_sessionid),
                             user_id: Optional[str] = Query(None, description="Instagram numeric user PK."),
                             username: Optional[str] = Query(None, description="Instagram username."),
                             amount: int = Query(50, ge=1, le=200),
                             cursor: str = Query(""),
                             clients: ClientStorage = Depends(get_clients)) -> MediaPage:
    """Get a page of media where a user is tagged
    """
    cl = await clients.get(sessionid)
    return await _user_tagged_medias_page(cl, user_id, username, amount, cursor)


@user_router.get("/reels", response_model=MediaPage)
async def user_clips(sessionid: str = Depends(get_sessionid),
                     user_id: Optional[str] = Query(None, description="Instagram numeric user PK."),
                     username: Optional[str] = Query(None, description="Instagram username."),
                     amount: int = Query(50, ge=1, le=200),
                     cursor: str = Query(""),
                     clients: ClientStorage = Depends(get_clients)) -> MediaPage:
    """Get a user's Reels page with the next pagination cursor
    """
    cl = await clients.get(sessionid)
    return await _user_clips_page(cl, user_id, username, amount, cursor)


@user_router.get("/videos", response_model=MediaPage)
async def user_videos(sessionid: str = Depends(get_sessionid),
                      user_id: Optional[str] = Query(None, description="Instagram numeric user PK."),
                      username: Optional[str] = Query(None, description="Instagram username."),
                      amount: int = Query(50, ge=1, le=200),
                      cursor: str = Query(""),
                      clients: ClientStorage = Depends(get_clients)) -> MediaPage:
    """Get a user's video page with the next pagination cursor
    """
    cl = await clients.get(sessionid)
    return await _user_videos_page(cl, user_id, username, amount, cursor)


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
                     usertags: Optional[List[str]] = Form([], description=USERTAGS_FORM_DESCRIPTION),
                     location: Optional[str] = Form(None, description=LOCATION_FORM_DESCRIPTION),
                     clients: ClientStorage = Depends(get_clients)) -> Dict:
    """Edit caption for media
    """
    cl = await clients.get(sessionid)
    return await cl.media_edit(
        media_id,
        caption,
        title,
        parse_upload_usertags(usertags),
        parse_upload_location(location),
    )


@router.get("/author", response_model=UserShort)
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


@router.get("/comments", response_model=CommentPage)
async def media_comments(sessionid: str = Depends(get_sessionid),
                         media_id: str = Query(...),
                         amount: int = Query(20, ge=1, le=200),
                         cursor: str = Query(""),
                         clients: ClientStorage = Depends(get_clients)) -> CommentPage:
    """Get a page of media comments
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.media_comments_chunk(media_id, amount, cursor or None)
    return CommentPage(items=items, next_cursor=next_cursor or "")


@router.get("/comments/stream", response_model=CommentStreamPage)
async def media_comments_stream(sessionid: str = Depends(get_sessionid),
                                media_id: str = Query(...),
                                min_id: str = Query(""),
                                max_id: str = Query(""),
                                clients: ClientStorage = Depends(get_clients)) -> CommentStreamPage:
    """Get a stream page of media comments
    """
    cl = await clients.get(sessionid)
    items, min_cursor, max_cursor = await cl.media_stream_comments_v1_chunk(media_id, min_id, max_id)
    return CommentStreamPage(items=items, min_cursor=min_cursor or "", max_cursor=max_cursor or "")


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


@router.get("/comment/infos", response_model=Dict[str, Any])
async def media_comment_infos(sessionid: str = Depends(get_sessionid),
                              media_ids: List[str] = Query(...),
                              clients: ClientStorage = Depends(get_clients)) -> Dict[str, Any]:
    """Get media comment summaries
    """
    cl = await clients.get(sessionid)
    return await cl.media_comment_infos(media_ids)


@router.post("/comment/check/offensive", response_model=bool)
async def media_comment_check_offensive(sessionid: str = Depends(get_sessionid),
                                        media_id: str = Form(...),
                                        text: str = Form(...),
                                        clients: ClientStorage = Depends(get_clients)) -> bool:
    """Check whether comment text is offensive for media
    """
    cl = await clients.get(sessionid)
    return await cl.media_check_offensive_comment(media_id, text)


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


@router.get("/comment/likers", response_model=List[Dict[str, Any]])
async def media_comment_likers(sessionid: str = Depends(get_sessionid),
                               comment_pk: str = Query(...),
                               amount: int = Query(0, ge=0, le=200),
                               clients: ClientStorage = Depends(get_clients)) -> List[Dict[str, Any]]:
    """Get users who liked a comment
    """
    cl = await clients.get(sessionid)
    return await cl.comment_likers_gql(comment_pk, amount)


@router.post("/comment/pin", response_model=bool)
async def media_comment_pin(sessionid: str = Depends(get_sessionid),
                            media_id: str = Form(...),
                            comment_pk: int = Form(...),
                            revert: Optional[bool] = Form(False),
                            clients: ClientStorage = Depends(get_clients)) -> bool:
    """Pin a media comment
    """
    cl = await clients.get(sessionid)
    return await cl.comment_pin(media_id, comment_pk, revert)


@router.delete("/comment/pin", response_model=bool)
async def media_comment_unpin(sessionid: str = Depends(get_sessionid),
                              media_id: str = Query(...),
                              comment_pk: int = Query(...),
                              clients: ClientStorage = Depends(get_clients)) -> bool:
    """Unpin a media comment
    """
    cl = await clients.get(sessionid)
    return await cl.comment_unpin(media_id, comment_pk)


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
