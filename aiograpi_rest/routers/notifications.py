from typing import Dict, List

from fastapi import APIRouter, Depends, Form, HTTPException, Query

from aiograpi_rest.dependencies import ClientStorage, get_clients, get_sessionid

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    responses={404: {"description": "Not found"}},
)

SETTING_VALUES = ["off", "following_only", "everyone"]
SETTING_CONTENT_TYPES = [
    "likes",
    "like_and_comment_on_photo_user_tagged",
    "user_tagged",
    "comments",
    "comment_likes",
    "first_post",
    "new_follower",
    "follow_request_accepted",
    "connection_notification",
    "tagged_in_bio",
    "pending_direct_share",
    "direct_share_activity",
    "direct_group_requests",
    "video_call",
    "rooms",
    "live_broadcast",
    "felix_upload_result",
    "view_count",
    "fundraiser_creator",
    "fundraiser_supporter",
    "notification_reminders",
    "announcements",
    "report_updated",
    "login_notification",
]


@router.get("", response_model=Dict)
async def notifications(
    sessionid: str = Depends(get_sessionid),
    mark_as_seen: bool = Query(False),
    clients: ClientStorage = Depends(get_clients),
) -> Dict:
    """Get notification inbox
    """
    cl = await clients.get(sessionid)
    return await cl.news_inbox_v1(mark_as_seen)


@router.get("/settings", response_model=Dict[str, List[str]])
async def notifications_settings(
    sessionid: str = Depends(get_sessionid),
) -> Dict[str, List[str]]:
    """Get supported notification settings
    """
    return {"content_types": SETTING_CONTENT_TYPES, "setting_values": SETTING_VALUES}


@router.patch("/settings", response_model=bool)
async def notifications_settings_update(
    sessionid: str = Depends(get_sessionid),
    content_type: str = Form(...),
    setting_value: str = Form(...),
    clients: ClientStorage = Depends(get_clients),
) -> bool:
    """Update notification settings
    """
    if content_type not in SETTING_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported content_type")
    if setting_value not in SETTING_VALUES:
        raise HTTPException(status_code=422, detail="Unsupported setting_value")
    cl = await clients.get(sessionid)
    return await cl.notification_settings(content_type, setting_value)
