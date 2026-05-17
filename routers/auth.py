import json
from typing import Dict, List, Optional, Union
from unittest.mock import patch

from fastapi import APIRouter, Depends, Form, HTTPException

from dependencies import ClientStorage, get_clients, get_optional_sessionid, get_sessionid

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
    responses={404: {"description": "Not found"}}
)


@router.post("/login")
async def auth_login(username: str = Form(...),
                     password: str = Form(...),
                     verification_code: Optional[str] = Form(
                         "",
                         description=(
                             "Two-factor authentication code from SMS, email, or TOTP. "
                             "When Instagram returns TwoFactorRequired, retry POST /auth/login "
                             "with the same username and password plus this value."
                         ),
                     ),
                     proxy: Optional[str] = Form(""),
                     locale: Optional[str] = Form(""),
                     timezone: Optional[str] = Form(""),
                     clients: ClientStorage = Depends(get_clients)) -> Union[str, bool]:
    """Login by username and password with 2FA
    """
    cl = clients.client()
    if proxy != "":
        cl.set_proxy(proxy)

    if locale != "":
        cl.set_locale(locale)

    if timezone != "":
        cl.set_timezone_offset(timezone)

    # Handle 2FA if verification code is provided
    if verification_code:
        # Try login with 2FA code directly
        try:
            result = await cl.login(username, password, verification_code=verification_code)
        except TypeError:
            # Fallback to mocking input if the direct parameter doesn't work
            with patch('builtins.input', return_value=verification_code):
                result = await cl.login(username, password)
    else:
        # Regular login without 2FA
        result = await cl.login(username, password)

    if result:
        clients.set(cl)
        return cl.sessionid
    return result


@router.post("/login/by/sessionid")
async def auth_login_by_sessionid(sessionid: str = Form(...),
                                  clients: ClientStorage = Depends(get_clients)) -> Union[str, bool]:
    """Login by sessionid
    """
    cl = clients.client()
    result = await cl.login_by_sessionid(sessionid)
    if result:
        clients.set(cl)
        return cl.sessionid
    return result


@router.patch("/relogin")
async def auth_relogin(sessionid: str = Depends(get_sessionid),
                       clients: ClientStorage = Depends(get_clients)) -> bool:
    """Relogin by username and password (with clean cookies)
    """
    cl = await clients.get(sessionid)
    return await cl.relogin()


@router.get("/settings")
async def settings_get(sessionid: str = Depends(get_sessionid),
                       clients: ClientStorage = Depends(get_clients)) -> Dict:
    """Get client's settings
    """
    cl = await clients.get(sessionid)
    return cl.get_settings()


@router.patch("/settings")
async def settings_set(settings: Optional[str] = Form(
                           None,
                           description=(
                               "JSON string from aiograpi Client.get_settings(). "
                               "Required when importing settings without an existing session."
                           ),
                       ),
                       proxy: Optional[str] = Form(
                           None,
                           description="Optional proxy URL to apply to the saved session. Pass an empty value to clear it.",
                       ),
                       locale: Optional[str] = Form(
                           None,
                           description="Optional locale such as en_US.",
                       ),
                       timezone: Optional[str] = Form(
                           None,
                           description="Optional timezone offset in seconds, for example 10800.",
                       ),
                       sessionid: str = Depends(get_optional_sessionid),
                       clients: ClientStorage = Depends(get_clients)) -> str:
    """Set client's settings
    """
    if sessionid != "":
        cl = await clients.get(sessionid)
    else:
        if settings is None:
            raise HTTPException(status_code=422, detail="settings is required when importing a new session")
        cl = clients.client()
    if settings is not None:
        cl.set_settings(json.loads(settings))
        await cl.expose()
    elif proxy is None and locale is None and timezone is None:
        raise HTTPException(status_code=422, detail="settings, proxy, locale, or timezone is required")
    if proxy is not None:
        cl.set_proxy(proxy or None)
    if locale:
        cl.set_locale(locale)
    if timezone:
        cl.set_timezone_offset(timezone)
    clients.set(cl)
    return cl.sessionid


@router.get("/timeline/feed")
async def timeline_feed(sessionid: str = Depends(get_sessionid),
                        clients: ClientStorage = Depends(get_clients)) -> Dict:
    """Get your timeline feed
    """
    cl = await clients.get(sessionid)
    return await cl.get_timeline_feed()


@router.post("/totp/enable", response_model=List[str])
async def totp_enable(verification_code: str = Form(...),
                      sessionid: str = Depends(get_sessionid),
                      clients: ClientStorage = Depends(get_clients)) -> List[str]:
    """Enable TOTP two-factor authentication
    """
    cl = await clients.get(sessionid)
    return await cl.totp_enable(verification_code)


@router.delete("/totp", response_model=bool)
async def totp_disable(sessionid: str = Depends(get_sessionid),
                       clients: ClientStorage = Depends(get_clients)) -> bool:
    """Disable TOTP two-factor authentication
    """
    cl = await clients.get(sessionid)
    return await cl.totp_disable()


@router.post("/challenge/resolve", response_model=bool)
async def challenge_resolve(last_json: str = Form(...),
                            sessionid: str = Depends(get_sessionid),
                            clients: ClientStorage = Depends(get_clients)) -> bool:
    """Resolve an Instagram login challenge
    """
    try:
        payload = json.loads(last_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="last_json must be valid JSON")
    cl = await clients.get(sessionid)
    return await cl.challenge_resolve(payload)
