from typing import List

from aiograpi.types import Comment, DirectThread, Media, StoryArchiveDay, UserShort, Viewer
from pydantic import BaseModel


class MediaPage(BaseModel):
    items: List[Media]
    next_cursor: str


class CommentPage(BaseModel):
    items: List[Comment]
    next_cursor: str


class UserShortPage(BaseModel):
    items: List[UserShort]
    next_cursor: str


class DirectThreadPage(BaseModel):
    items: List[DirectThread]
    next_cursor: str


class ViewerPage(BaseModel):
    items: List[Viewer]
    next_cursor: str


class StoryArchiveDayPage(BaseModel):
    items: List[StoryArchiveDay]
    next_cursor: str
