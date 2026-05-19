from typing import List, Literal, Optional

from aiograpi.types import DirectMessage, DirectThread, UserShort
from fastapi import APIRouter, Depends, Form, HTTPException, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid
from aiograpi_rest.pagination import DirectThreadPage

router = APIRouter(
    prefix="/direct",
    tags=["Direct"],
    responses={404: {"description": "Not found"}},
)


@router.get("/inbox", response_model=DirectThreadPage)
async def direct_inbox(
    sessionid: str = Depends(get_sessionid),
    selected_filter: Literal["", "flagged", "unread"] = Query(""),
    box: Literal["", "general", "primary"] = Query(""),
    thread_message_limit: Optional[int] = Query(None),
    cursor: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> DirectThreadPage:
    """Get a page of direct inbox threads
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.direct_threads_chunk(
        selected_filter,
        box,
        thread_message_limit,
        cursor or None,
    )
    return DirectThreadPage(items=items, next_cursor=next_cursor or "")


@router.get("/threads", response_model=List[DirectThread])
async def direct_threads(
    sessionid: str = Depends(get_sessionid),
    amount: int = Query(20),
    selected_filter: Literal["", "flagged", "unread"] = Query(""),
    box: Literal["", "general", "primary"] = Query(""),
    thread_message_limit: Optional[int] = Query(None),
    clients: ClientStorage = Depends(get_clients),
) -> List[DirectThread]:
    """List direct threads
    """
    cl = await clients.get(sessionid)
    return await cl.direct_threads(amount, selected_filter, box, thread_message_limit)


@router.get("/thread", response_model=DirectThread)
async def direct_thread(
    sessionid: str = Depends(get_sessionid),
    thread_id: int = Query(...),
    amount: int = Query(20),
    clients: ClientStorage = Depends(get_clients),
) -> DirectThread:
    """Get direct thread details
    """
    cl = await clients.get(sessionid)
    return await cl.direct_thread(thread_id, amount)


@router.get("/messages", response_model=List[DirectMessage])
async def direct_messages(
    sessionid: str = Depends(get_sessionid),
    thread_id: int = Query(...),
    amount: int = Query(20),
    clients: ClientStorage = Depends(get_clients),
) -> List[DirectMessage]:
    """List messages in a direct thread
    """
    cl = await clients.get(sessionid)
    return await cl.direct_messages(thread_id, amount)


@router.get("/message", response_model=DirectMessage)
async def direct_message(
    sessionid: str = Depends(get_sessionid),
    thread_id: int = Query(...),
    message_id: int = Query(...),
    amount: int = Query(20),
    clients: ClientStorage = Depends(get_clients),
) -> DirectMessage:
    """Get a direct message
    """
    cl = await clients.get(sessionid)
    return await cl.direct_message(thread_id, message_id, amount)


@router.get("/pending", response_model=DirectThreadPage)
async def direct_pending(
    sessionid: str = Depends(get_sessionid),
    cursor: str = Query(""),
    clients: ClientStorage = Depends(get_clients),
) -> DirectThreadPage:
    """List pending direct thread requests
    """
    cl = await clients.get(sessionid)
    items, next_cursor = await cl.direct_pending_chunk(cursor or None)
    return DirectThreadPage(items=items, next_cursor=next_cursor or "")


@router.get("/search", response_model=List[UserShort])
async def direct_search(
    sessionid: str = Depends(get_sessionid),
    query: str = Query(...),
    mode: Literal["raven", "universal"] = Query("universal"),
    clients: ClientStorage = Depends(get_clients),
) -> List[UserShort]:
    """Search direct recipients
    """
    cl = await clients.get(sessionid)
    return await cl.direct_search(query, mode)


@router.post("/thread", response_model=str)
async def direct_thread_create(
    sessionid: str = Depends(get_sessionid),
    user_ids: List[int] = Form(...),
    title: str = Form(""),
    clients: ClientStorage = Depends(get_clients),
) -> str:
    """Create a direct thread
    """
    if len(user_ids) < 2:
        raise HTTPException(
            status_code=422,
            detail="Group threads require at least two recipient user_ids",
        )
    cl = await clients.get(sessionid)
    return await cl.direct_thread_create(user_ids, title)


@router.post("/message", response_model=DirectMessage)
async def direct_message_send(
    sessionid: str = Depends(get_sessionid),
    text: str = Form(...),
    user_ids: List[int] = Form([]),
    thread_ids: List[int] = Form([]),
    send_attribute: str = Form("message_button"),
    clients: ClientStorage = Depends(get_clients),
) -> DirectMessage:
    """Send a direct message
    """
    if bool(user_ids) == bool(thread_ids):
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one of user_ids or thread_ids",
        )
    cl = await clients.get(sessionid)
    return await cl.direct_send(text, user_ids, thread_ids, send_attribute)


@router.delete("/message", response_model=bool)
async def direct_message_delete(
    sessionid: str = Depends(get_sessionid),
    thread_id: int = Query(...),
    message_id: int = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Delete a direct message
    """
    cl = await clients.get(sessionid)
    return await cl.direct_message_delete(thread_id, message_id)


@router.patch("/message/seen", response_model=bool)
async def direct_message_seen(
    sessionid: str = Depends(get_sessionid),
    thread_id: int = Form(...),
    message_id: int = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Mark a direct message as seen
    """
    cl = await clients.get(sessionid)
    return await cl.direct_message_seen(thread_id, message_id)
