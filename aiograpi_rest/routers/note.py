from typing import List

from aiograpi.types import Note
from fastapi import APIRouter, Depends, Form, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid

router = APIRouter(
    tags=["Note"],
    responses={404: {"description": "Not found"}},
)


@router.get("/notes", response_model=List[Note])
async def notes(
    sessionid: str = Depends(get_sessionid),
    clients: ClientStorage = Depends(get_clients),
) -> List[Note]:
    """List notes
    """
    cl = await clients.get(sessionid)
    return await cl.get_notes()


@router.post("/note", response_model=Note)
async def note_create(
    sessionid: str = Depends(get_sessionid),
    text: str = Form(...),
    audience: int = Form(0),
    clients: ClientStorage = Depends(get_clients),
) -> Note:
    """Create a note
    """
    cl = await clients.get(sessionid)
    return await cl.create_note(text, audience)


@router.delete("/note", response_model=bool)
async def note_delete(
    sessionid: str = Depends(get_sessionid),
    note_id: int = Query(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Delete a note
    """
    cl = await clients.get(sessionid)
    return await cl.delete_note(note_id)
