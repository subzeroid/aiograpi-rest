# Changelog

## Unreleased

### Added

- `GET /user/followers/gql` and `GET /user/following/gql`: follower and
  following pages through aiograpi's private GraphQL list methods
  (`user_followers_private_gql_chunk`, `user_following_private_gql_chunk`).
  They take the same `user_id`, `amount` and `cursor` and return the same
  `items` and `next_cursor` as the v1 routes. See "Follower and following
  lists" in `docs/api.md` for live observations on throttling and cursors.

## v6.0.0 - 2026-05-21

Release: <https://github.com/subzeroid/aiograpi-rest/releases/tag/v6.0.0>

### Changed

- Upgraded the wrapped client to `aiograpi==1.0.9`.
- Updated the package version to `6.0.0`.
- Reworked account password and email flows for current aiograpi semantics:
  `POST /account/password/reset`, `POST /account/email/confirmation`, and
  `POST /account/email/confirm`.
- Updated Reel upload with music to use aiograpi's current
  `clip_upload_with_music` method and expose the new optional upload fields.

### Added

- Direct routes for request previews, channels, interop upgrade status, GenAI
  bot suggestions, and E2EE eligibility.
- Music routes for current catalog search, keyword search, trending music, top
  trends, Reels music browsing, audio bookmarking, and original-audio title
  availability.
- Media note routes: `POST /media/note` and `DELETE /media/note`.

### Removed

- Removed the public `GET /hashtag/related` route because aiograpi 1.0.x no
  longer exposes `hashtag_related_hashtags`.

### Verified

- Offline test gate: `270 passed, 6 deselected`, `100.00%` coverage.
- Live smoke gate: `/user/about`, paginated reads, story upload/read/download
  cleanup, and media upload/edit/delete state checks passed on Python 3.13.
- Release workflow verified PyPI, Docker Hub, GHCR, GitHub Release artifacts,
  and a smoke test of the published Docker image.
