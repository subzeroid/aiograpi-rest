# API Guide

## Authentication

Protected routes accept the saved session ID through the `X-Session-ID` header.
Swagger UI exposes this through the green **Authorize** button.

Session-creation routes:

- `POST /auth/login`
- `POST /auth/login/by/sessionid`
- `PATCH /auth/settings` accepts an optional saved session and returns a new
  session ID after settings are loaded.

Session-aware routes still accept legacy `sessionid` values from query
parameters, form data, or a `sessionid` cookie for backwards compatibility.

## Route Conventions

- `GET` routes read or download data.
- `POST` routes create sessions, create actions, or upload media.
- `PATCH` routes update state.
- `DELETE` routes remove or undo state.
- Paths use slash-separated resources such as `/story/upload/by/url`.
- State reversals use the same resource path with `DELETE`: for example,
  `POST /media/like` likes media and `DELETE /media/like` unlikes it.

## OpenAPI

- Swagger UI: `/docs`
- Raw schema: `/openapi.json`

The schema uses client-friendly operation IDs and request schema names so it can
be passed directly into OpenAPI client generators.

## Pagination

`GET /media/user/medias` returns a plain list for simple reads.
`GET /media/user/medias/paginated` returns an object with `items` and
`end_cursor`; pass the returned `end_cursor` into the next request to continue
from the previous page.

## System Endpoints

- `GET /health` returns `{"status":"ok"}` for liveness.
- `GET /ready` checks storage and required runtime dependencies.
- `GET /metrics` exports Prometheus text metrics.
- `GET /build` returns service build metadata.
- `GET /deps` returns runtime dependency versions.
