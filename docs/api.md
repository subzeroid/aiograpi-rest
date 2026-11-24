# API Guide

This guide is current for `aiograpi-rest v6.0.0`, which wraps
`aiograpi==1.0.9`.

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

`GET /auth/totp/seed` generates a TOTP seed for the authenticated session.
`GET /auth/totp/code?seed=...` generates the current six-digit TOTP code from a
seed without requiring a session.

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

## Relationship Actions

User relationship routes use `POST` to create or enable a relationship state and
`DELETE` to remove or disable it.

- `POST /user/follow` follows a user.
- `DELETE /user/follow` unfollows a user.
- `DELETE /user/follower` removes a follower.
- `POST /account/follow/request/approve` approves a pending follow request.
- `DELETE /account/follow/request` declines a pending follow request.
- `POST /account/follow/requests/approve` approves multiple pending follow requests.
- `DELETE /account/follow/requests` declines multiple pending follow requests.
- `POST /user/close-friend` adds a user to close friends.
- `DELETE /user/close-friend` removes a user from close friends.
- `POST /user/notifications/posts` enables post notifications for a user.
- `DELETE /user/notifications/posts` disables post notifications for a user.
- `POST /user/notifications/stories` enables story notifications for a user.
- `DELETE /user/notifications/stories` disables story notifications for a user.
- `POST /user/notifications/reels` enables Reel notifications for a user.
- `DELETE /user/notifications/reels` disables Reel notifications for a user.
- `POST /user/notifications/videos` enables video notifications for a user.
- `DELETE /user/notifications/videos` disables video notifications for a user.

## Account Settings

- `GET /account/security` returns security metadata for the authenticated
  account.
- `PATCH /account/biography` updates only the authenticated account biography.
- `PATCH /account/external-url` replaces the authenticated account external
  profile URL.
- `DELETE /account/external-url` clears the authenticated account external URL
  by asking Instagram to replace it with an empty URL. If Instagram rejects an
  empty URL for the account, remove the concrete bio link via
  `DELETE /account/bio-links`.
- `DELETE /account/bio-links` removes one or more bio links by `link_ids`.
- `PATCH /account/password` changes the authenticated account password.
- `POST /account/password/reset` requests a password reset link or code by
  username, email, or phone `identifier`.
- `POST /account/email/confirmation` sends an email confirmation code.
- `POST /account/email/confirm` confirms a pending email change with `email`
  and `code`.
- `POST /account/phone/confirm` sends a phone confirmation code.

## Notification Settings

- `GET /notifications/settings` returns supported notification `content_type`
  values and allowed setting values.
- `PATCH /notifications/settings` updates one notification setting by
  `content_type` and `setting_value`. Most notification settings accept `off`,
  `following_only`, or `everyone`.
- `PATCH /notifications/settings` with `content_type=mute_all` accepts only
  `cancel`, `15_minutes`, `1_hour`, `2_hour`, `4_hour`, or `8_hour`.
- `DELETE /notifications/settings` disables all supported notification
  settings for the authenticated account.

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
- `GET /search/top/flat` returns the older flat blended top-search list.
- `GET /search/web/top` returns web top-search results.
- `GET /search/web/hashtags` returns web hashtag search results.
- `GET /search/reels` returns Reel search results.
- `GET /search/item` returns one raw Instagram search tab by `item_id` and
  `search_surface`.
- `GET /search/suggested/users` returns suggested users for a profile.
- `GET /search/recent` returns the authenticated account's recent searches.
- `GET /search/typeahead` returns autocomplete suggestions for a partial query.
- `GET /search/typeahead/stream` returns the raw typeahead stream envelope.
- `GET /search/typeahead/users` returns flattened typeahead user suggestions.

`/search/top`, `/search/top/flat`, `/search/web/top`, `/search/reels`,
`/search/accounts`, `/search/typeahead`, `/search/typeahead/stream`, and
`/search/item` return raw Instagram-shaped objects because their payloads vary
by ranking surface and cursor state.

## Share

Share routes decode Instagram share URLs or encoded share codes without creating
or changing Instagram state.

- `GET /share?url=...` returns the decoded share `type`, `pk`, and extracted
  `code` for a share URL.
- `GET /share?code=...` returns the decoded share `type`, `pk`, and original
  `code` for an encoded share code.

## Highlight

Highlight routes manage Story highlights and accept either the Instagram
highlight PK or a highlight URL where lookup can be resolved from a URL:

- `GET /highlight?highlight_pk=...` returns highlight details by PK.
- `GET /highlight?url=...` resolves the PK from the URL and returns highlight
  details.
- `PATCH /highlight` updates title, cover, and story membership. A title-only
  patch uses aiograpi's dedicated title-change method, and `cover_picture`
  uploads a cover image through aiograpi's dedicated cover-change method.

## Story

Story archive routes expose both archive day pages and the actual archived
story media collection:

- `GET /story/archive` returns paginated archive day groups with `items` and
  `next_cursor`.
- `GET /story/archive/media` returns archived stories from the authenticated
  account. Pass `amount=0` to keep aiograpi's default of returning all
  available archived stories, or a positive amount to limit the list.
- `GET /story/stickers` returns Instagram's raw story sticker tray payload for
  building story upload decorations.
- `GET /story/users` returns story lists for multiple users. Pass repeated
  `user_ids` query parameters, for example
  `user_ids=123&user_ids=456`.

## ID Parameters

Instagram user primary keys are exposed as strings in the REST API. Use
`user_id=25025320` for a single user and repeat `user_ids` for lists, for
example `user_ids=123&user_ids=456`. Treat them as opaque IDs in generated
clients even when they contain only digits.

## User Discovery

User discovery routes live under the target user context and return raw
Instagram-shaped objects where `aiograpi` exposes variable discovery payloads:

- `GET /user/suggestions` returns suggested users for a target profile.
- `GET /user/suggestions/details` returns expanded social context for
  suggestion IDs from `/user/suggestions`.
- `GET /user/recommendations` returns category-based recommended accounts for a
  target profile.
- `GET /user/featured/accounts` returns Instagram's featured-account
  suggestions for a target profile.
- `GET /user/fundraiser` returns standalone fundraiser info for a target
  profile.
- `GET /user/creator` returns creator metadata for a target profile as
  `{ "user": ..., "info": ... }`.
- `GET /user/profile/web` returns Instagram's web-profile payload for a
  username.
- `GET /user/stream` returns a profile stream by `user_id` or `username`.
  `view=flat` returns the merged user payload; `view=raw` returns Instagram's
  stream envelope.
- `GET /user/friendships` returns relationship summaries for repeated
  `user_ids` query parameters.

`GET /account/feed/new` belongs to the authenticated account context and returns
whether Instagram says new timeline feed items are available.
`GET /account/feed/user/stream-item` returns a feed stream item for the
authenticated account.
`GET /account/family` returns Instagram's account-family payload for the
authenticated account.

## Reels

Global Reels feed routes live under the `Reels` tag and return arrays of media
objects. They accept `amount` and `last_media_pk` where the underlying
`aiograpi` method supports feed continuation.

- `GET /reels` returns connected Reels media.
- `GET /reels/friends` returns Friends tab Reels media.
- `GET /reels/explore` returns Explore Reels media.
- `GET /reels/timeline` returns Reels media for a `collection_pk`.

Clip upload and utility routes live under the `Clip (Reels)` tag:

- `GET /clip/creation/info` returns the raw Reel creation preflight config.
- `GET /clip/trial-eligibility` checks whether Trial Reels are enabled for the
  authenticated account.
- `GET /clip/share/facebook/config` returns Facebook sharing config; pass
  `device_status` as an optional JSON-encoded query parameter.
- `GET /clip/template` returns the raw clip template payload for a source
  `media_id`.
- `POST /clip/upload` uploads a Reel from a video file.
- `POST /clip/upload/by/url` uploads a Reel from a video URL.
- `POST /clip/upload/with/music` uploads a Reel from a video file with a
  JSON-encoded `track` payload and optional JSON-encoded `extra_data`.
- `POST /clip/pin` pins a Reel by `media_pk`.
- `DELETE /clip/pin` unpins a Reel by `media_pk`.

## Saved Collections

Saved collection routes live under the authenticated account context because
they read the current account's saved Instagram collections.

- `GET /account/collections` lists saved collections.
- `GET /account/collection` gets one saved collection by `collection_pk` or `name`.
- `GET /account/collection/media` lists media in one saved collection by
  `collection_pk` or `name`.
- `GET /account/archive/media` lists archived media for the authenticated
  account with `items` and `next_cursor`.

## Explore

Explore routes return raw Instagram-shaped objects because the Explore payload
depends on ranking, layout, and media type.

- `GET /explore` returns the authenticated account's Explore page.
- `GET /explore/media` returns Explore metadata for one `media_pk`.

## Tracks And Music

Track routes return Instagram music track data for Reels and post creation
workflows.

- `GET /track` gets a track by `id` or `canonical_id`.
- `GET /track/stream` returns streamed media for a track `id`.
- `GET /track/download/by/url` downloads track audio from a URL.
- `GET /music/feed/browser` returns music candidates for feed posts.
- `GET /music/search` searches the current app music catalog.
- `GET /music/keywords` searches music typeahead keywords.
- `GET /music/trending` returns trending music candidates.
- `GET /music/trends/top` returns top music trends.
- `GET /music/clips/browser` returns music candidates for Reels.
- `POST /music/bookmark` bookmarks original audio.
- `GET /music/original-audio/title/availability` checks whether an original
  audio title is valid.

## Livestreams

Livestream routes manage the authenticated account's Instagram Live broadcast
state. They are exposed as resource state changes instead of `start`/`end`
action paths:

- `POST /media/livestream` creates a live broadcast and returns stream server
  metadata.
- `GET /media/livestream` returns broadcast info by `broadcast_id`.
- `PATCH /media/livestream` changes the broadcast `state` to `started` or
  `ended`.
- `GET /media/livestream/comments` lists live comments for a `broadcast_id`.
- `GET /media/livestream/viewers` lists live viewers for a `broadcast_id`.
- `POST /media/note` creates a note attached to a media item.
- `DELETE /media/note` deletes a media-attached note by `note_id`.

## Notes

- `GET /notes` lists visible notes.
- `GET /note` returns a visible note by `username`.
- `GET /note/text` returns only the visible note text by `username`.
- `POST /note` creates a text note.
- `POST /note/music` creates a note with music from a track payload returned by
  `GET /notes/music/browser`.
- `PATCH /notes/last-seen` marks notes as seen.
- `DELETE /note` deletes one note by `note_id`.
- `GET /notes/music/browser` returns music candidates for Notes.

## Comment Utilities

Comment routes live under `Media (Post)` because Instagram comments always
belong to a media object.

- `GET /media/comments` lists a paginated comment page with `next_cursor`.
- `GET /media/comments/stream` lists a stream comment page with `min_cursor`
  and `max_cursor`.
- `POST /media/comment` creates a comment or reply.
- `DELETE /media/comment` deletes one comment from media.
- `GET /media/comment/replies` lists replies for one comment.
- `POST /media/comment/like` likes a comment.
- `DELETE /media/comment/like` unlikes a comment.
- `GET /media/comment/likers` lists users who liked a comment.
- `POST /media/comment/pin` pins a comment.
- `DELETE /media/comment/pin` unpins a comment.
- `GET /media/comment/infos` returns comment counters for media IDs.
- `POST /media/comment/check/offensive` checks whether text is offensive for
  the target media.

## Direct

- `GET /direct/channels` lists Direct channels, optionally filtered by
  `user_id` and repeated `thread_subtypes`.
- `GET /direct/interop/upgraded` reports whether the account has upgraded
  interop messaging.
- `GET /direct/requests/preview` returns a lightweight pending requests
  preview.
- `GET /direct/genai/bots` lists generated AI bot suggestions for Direct.
- `PATCH /direct/e2ee/eligibility` updates the account's Direct E2EE
  eligibility state.
- `GET /direct/pending/inbox` lists pending direct request threads up to
  `amount`.
- `GET /direct/spam/inbox` lists spam direct request threads up to `amount`.
- `POST /direct/request/approve` approves a direct message request thread.
- `POST /direct/thread/message` replies in an existing direct thread.
- `DELETE /direct/message` unsends a direct message.
- `POST /direct/cutout/sticker` sends a cutout sticker to either `user_ids`
  or `thread_ids`.
- `POST /direct/video/upload` uploads a video through aiograpi's story-direct
  flow with `caption`, optional `thumbnail`, repeatable JSON `mentions` and
  `medias`, required `thread_ids`, and optional JSON `extra_data`.

## Pagination

Paginated read-list routes return an object with `items` and `next_cursor`.
Pass the returned `next_cursor` as `cursor` on the next request to continue
from the previous page. This shape is used for:

- `GET /direct/inbox`
- `GET /direct/pending`
- `GET /direct/spam`
- `GET /account/archive/media`
- `GET /hashtag/media/recent`
- `GET /hashtag/media/top`
- `GET /location/media/recent`
- `GET /location/media/top`
- `GET /media/comments`
- `GET /media/comments/stream` returns `items`, `min_cursor`, and `max_cursor`
  instead of `next_cursor`.
- `GET /story/archive`
- `GET /story/viewers`
- `GET /user/reels`
- `GET /account/follow/requests`
- `GET /user/followers`
- `GET /user/followers/gql`
- `GET /user/following`
- `GET /user/following/gql`
- `GET /user/posts`
- `GET /user/tagged/posts`
- `GET /user/videos`

### Follower and following lists: v1 or private GraphQL

There are two routes for each list:

| Route | aiograpi method | Instagram call |
|-------|-----------------|----------------|
| `GET /user/followers` | `user_followers_v1_chunk` | `GET /api/v1/friendships/{id}/followers/` |
| `GET /user/followers/gql` | `user_followers_private_gql_chunk` | private GraphQL `FollowersList` (Android app) |
| `GET /user/following` | `user_following_v1_chunk` | `GET /api/v1/friendships/{id}/following/` |
| `GET /user/following/gql` | `user_following_private_gql_chunk` | private GraphQL `FollowingList` (Android app) |

What we saw on a live account (November 2026, aiograpi 2.1.15):

- **Instagram throttles the v1 followers list per account and endpoint.** After
  about 120 v1 followers pages in roughly 14 hours, every
  `friendships/{id}/followers` call answered HTTP 429 (`ClientThrottledError`),
  for any target user. In the same minutes, v1 `following`, media comments,
  media likers and user info calls kept answering 200.
- **The private GraphQL list kept answering 200 for the same account while the
  v1 list was throttled.** Its payload root is
  `xdt_api__v1__friendships__followers`, so it is served by the same backend
  list, but Instagram counted it separately.
- **The cursors are the same kind.** A v1 `next_cursor` (`"847|AQH…"`) passed as
  `cursor` to `/user/followers/gql` continued the list from that point (none of
  the first page came back) and returned a cursor in the same format
  (`"872|AQH…"`). A crawl can switch from v1 to GraphQL without starting over.
  We could not test the other direction while v1 was throttled.
- **GraphQL pages are smaller and start with a plain offset.** Starting
  without a cursor, pages held 25 users and the cursors were plain offsets
  (`"25"`, `"50"`). Consecutive pages repeated a few users (6 of 25 in one
  test), so de-duplicate by `pk`. `amount` only trims the page Instagram sends;
  it does not ask for more.

User post collection routes accept either `user_id` for numeric Instagram
user PKs or `username` for usernames. If a legacy client passes a username in
`user_id`, the service resolves it before calling `aiograpi`.

Additional discovery collection routes return plain arrays when `aiograpi` does
not expose a cursor for the underlying method:

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

Music upload endpoints also use JSON strings: `track` is a JSON-encoded
`Track` object returned by music search/browser routes, and `extra_data` is
optional configure data. This applies to:

- `POST /photo/upload/with/music`
- `POST /clip/upload/with/music`
- `POST /album/upload/with/music`

Media notes use the same JSON field style for optional `extra_data`:

- `POST /media/note`
- `DELETE /media/note`

`device_status` is an optional JSON object for
`GET /clip/share/facebook/config`.

## System Endpoints

- `GET /health` returns `{"status":"ok"}` for liveness.
- `GET /ready` checks storage and required runtime dependencies.
- `GET /metrics` exports Prometheus text metrics.
- `GET /build` returns service build metadata.
- `GET /deps` returns runtime dependency versions.
