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

### Session Client Options

`POST /auth/login` and `POST /auth/login/by/sessionid` accept optional `proxy`,
`locale`, and `timezone` form fields. The service persists the proxy separately
from `aiograpi` settings because `Client.get_settings()` does not include proxy
transport state.

Use `PATCH /auth/settings` to update an existing session after login. Send the
session through `X-Session-ID` or the legacy `sessionid` form field, then pass
any of:

- `settings`: a JSON string from `aiograpi.Client.get_settings()`.
- `proxy`: proxy URL for all restored clients. Pass an empty value to clear it.
- `locale`: locale such as `en_US`.
- `timezone`: timezone offset in seconds, such as `10800`.

### Two-Factor Login

If `POST /auth/login` returns `TwoFactorRequired`, retry the same endpoint with
the same `username` and `password` plus `verification_code`.

If it returns `ChallengeRequired`, resolve the Instagram challenge in the
account/session context first, then retry login or import a known-good saved
session through `PATCH /auth/settings`.

If the challenge asks for an SMS or email code, call
`POST /auth/challenge/resolve` with the same `last_json` challenge payload and
the `security_code` from Instagram. The service injects that code into
`aiograpi` for one request and restores the default handler afterwards, so the
server never waits for stdin.

If Instagram says the username does not belong to an account, the API returns
HTTP 401 with a hint to check the username and retry `POST /auth/login`.

If Instagram returns `FeedbackRequired`, `PleaseWaitFewMinutes`, or
`RateLimitError`, the API returns HTTP 429. These errors usually mean Instagram
is throttling the account or action; pause automation, reduce request rate, and
check account and proxy health before retrying.

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

## Search

Search routes live under the `Search` tag and hide Instagram's internal
`fbsearch` naming behind resource-oriented paths:

- `GET /search/users` searches accounts by query.
- `GET /search/accounts` searches accounts through Instagram's newer search
  surface and supports `page_token`.
- `GET /search/followers` searches inside a user's followers.
- `GET /search/following` searches inside accounts a user follows.
- `GET /search/hashtags` searches hashtags.
- `GET /search/music` searches music tracks.
- `GET /search/locations` searches locations by name or coordinates.
- `GET /search/places` searches places by query with optional `lat` and `lng`
  ranking context.
- `GET /search/top` returns Instagram's blended top search results.
- `GET /search/reels` returns Reel search results.
- `GET /search/recent` returns the authenticated account's recent searches.
- `GET /search/typeahead` returns autocomplete suggestions for a partial query.

`/search/top`, `/search/reels`, `/search/accounts`, and `/search/typeahead`
return raw Instagram-shaped objects because their payloads vary by ranking
surface and cursor state.

## Pagination

Paginated read-list routes return an object with `items` and `next_cursor`.
Pass the returned `next_cursor` as `cursor` on the next request to continue
from the previous page. This shape is used for:

- `GET /direct/inbox`
- `GET /hashtag/media/recent`
- `GET /hashtag/media/top`
- `GET /location/media/recent`
- `GET /location/media/top`
- `GET /media/comments`
- `GET /story/archive`
- `GET /story/viewers`
- `GET /user/reels`
- `GET /account/follow/requests`
- `GET /user/followers`
- `GET /user/following`
- `GET /user/posts`
- `GET /user/tagged/posts`
- `GET /user/videos`

User post collection routes accept either `user_id` for numeric Instagram
user PKs or `username` for usernames. If a legacy client passes a username in
`user_id`, the service resolves it before calling `aiograpi`.

Additional discovery collection routes return plain arrays when `aiograpi` does
not expose a cursor for the underlying method:

- `GET /hashtag/related`
- `GET /hashtag/reels`
- `GET /location/guides`
- `GET /user/guides`
- `GET /user/pinned/posts`

## Form JSON Fields

Story upload decoration fields such as `mentions`, `locations`, `links`,
`hashtags`, and `stickers` are form fields. Repeat the field with one
JSON-encoded object per value, or pass a single JSON array of objects.
For mentions, locations, and hashtags, omitted `x`, `y`, `width`, `height`, or
`rotation` values default to a centered story position before the request is
sent to `aiograpi`.

Feed upload and edit metadata use JSON-encoded form strings too. The upload
endpoints for photo, video, clip/Reels, IGTV, album/carousel, and the media
edit endpoint accept `usertags` as one JSON array or repeated JSON-encoded
`Usertag` values, and `location` as one JSON-encoded `Location` object. Leave
these fields empty or omit them when no metadata is needed.

## System Endpoints

- `GET /health` returns `{"status":"ok"}` for liveness.
- `GET /ready` checks storage and required runtime dependencies.
- `GET /metrics` exports Prometheus text metrics.
- `GET /build` returns service build metadata.
- `GET /deps` returns runtime dependency versions.
