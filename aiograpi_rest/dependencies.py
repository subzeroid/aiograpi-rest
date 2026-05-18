from typing import Generator, Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from aiograpi_rest.storages import ClientStorage

sessionid_header = APIKeyHeader(
    name="X-Session-ID",
    scheme_name="SessionId",
    description=(
        "Paste a saved aiograpi-rest sessionid. "
        "Get one from `POST /auth/login` or `POST /auth/login/by/sessionid`."
    ),
    auto_error=False,
)


def get_clients() -> Generator:
    try:
        clients = ClientStorage()
        yield clients
    finally:
        clients.close()


def _clean_sessionid(value: object) -> Optional[str]:
    if value is None:
        return None
    sessionid = str(value).strip()
    return sessionid or None


async def _resolve_sessionid(
    request: Request,
    header_sessionid: Optional[str],
) -> Optional[str]:
    sessionid = _clean_sessionid(header_sessionid)
    if sessionid:
        return sessionid

    sessionid = _clean_sessionid(request.cookies.get("sessionid"))
    if sessionid:
        return sessionid

    sessionid = _clean_sessionid(request.query_params.get("sessionid"))
    if sessionid:
        return sessionid

    content_type = request.headers.get("content-type", "").lower()
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        sessionid = _clean_sessionid(form.get("sessionid"))
        if sessionid:
            return sessionid

    return None


async def get_optional_sessionid(
    request: Request,
    header_sessionid: Optional[str] = Security(sessionid_header),
) -> str:
    return await _resolve_sessionid(request, header_sessionid) or ""


async def get_sessionid(
    request: Request,
    header_sessionid: Optional[str] = Security(sessionid_header),
) -> str:
    sessionid = await _resolve_sessionid(request, header_sessionid)
    if not sessionid:
        raise HTTPException(status_code=401, detail="Session ID required")
    return sessionid
