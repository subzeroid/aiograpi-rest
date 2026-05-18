# aiograpi-rest

`aiograpi-rest` is a RESTful HTTP service for
[`aiograpi`](https://github.com/subzeroid/aiograpi), the async Python wrapper for
Instagram's private mobile API.

Use it when your application is not written in Python, but you still want to run
the maintained `aiograpi` client behind a simple OpenAPI-compatible HTTP
boundary.

## What It Provides

- Login, relogin, session import, settings export/import, and runtime proxy,
  locale, and timezone updates.
- Account profile, privacy, profile picture, and authenticated account info.
- User profile, follower, following, follow, mute, block, search, friendship,
  follow request, highlight, and about endpoints.
- Media comments, likes, saves, pins, archive, photo, video, Reel, carousel
  album, story, highlight, note, Direct, notification, IGTV, and insights routes.
- OpenAPI documentation at `/docs` and raw schema at `/openapi.json`.
- Service health endpoints: `/health`, `/ready`, `/metrics`, `/build`, and `/deps`.
- Python package layout under `aiograpi_rest/`, with Docker and local uvicorn
  entrypoints using `aiograpi_rest.main:app`.

## What It Does Not Hide

Self-hosting means you still operate the Instagram accounts, proxies, session
storage, retries, and challenge handling. If you want a managed API instead,
see [HikerAPI](https://hikerapi.com/p/7RAo9ACK).

## Method Coverage

The service intentionally exposes a focused subset of `aiograpi.Client`. The
generated [aiograpi coverage report](aiograpi-coverage.md) lists every public
client method and whether it is reachable through a REST route.
