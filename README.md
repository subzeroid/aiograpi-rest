# aiograpi-rest

**RESTful HTTP service that wraps [`aiograpi`](https://github.com/subzeroid/aiograpi) (the async fork of `instagrapi`) so you can call Instagram's private API from any programming language.** Run it as a Docker sidecar next to your application; hit it from Node, Go, PHP, Java, C#, Ruby, Swift, Bash — anything that speaks HTTP.

This is the cross-language exit when your stack is not Python and the maintained Instagram libraries in your own language have gone stale or been archived (which, as of 2026, is most of them — see the [language-by-language survey](https://instagrapi.com/guides/instagram-api-libraries-by-language) on instagrapi.com).

Support chat on Telegram: https://t.me/aiograpi_support (the previous `@instagrapi` group was restricted by Meta and is no longer maintained)

## Why the project was renamed

Renamed from `instagrapi-rest` to `aiograpi-rest` in v1.0.0. The old name made
sense while the service wrapped synchronous `instagrapi`, but the service is now powered by `aiograpi`, the maintained async fork. The new name is more precise
for package managers, Docker images, OpenAPI clients, and repository discovery:
this project is the REST/HTTP boundary for `aiograpi`.

`aiograpi-rest` starts its own semver line at `1.0.0`. It is the renamed
successor of `instagrapi-rest 3.1.1`; the first aiograpi-rest release did not
continue the old package version number.

## Why this exists

`aiograpi` is the actively-maintained async Python wrapper for Instagram's private mobile API (the async fork of `instagrapi`) — full write surface (post, DM, story), pydantic-typed responses, first-class `challenge_required` and 2FA handling. If your application is in Python, you import it directly.

If your application is in a different language, your options for Instagram have been narrowing fast. The most-starred libraries on GitHub's [`instagram-api` topic](https://github.com/topics/instagram-api) are mostly stale or explicitly archived: the canonical Node/TypeScript client (`dilame/instagram-private-api`) hasn't shipped a meaningful release since August 2024; the canonical Go client (`ahmdrz/goinsta`) was archived in 2021; the Swift options are dead. Instagram's surface keeps moving and the per-language wrapper authors largely stopped chasing it.

`aiograpi-rest` solves that the simple way: run the actively-maintained async Python library (`aiograpi`) behind an HTTP boundary, and call it from whatever language you actually write your business logic in.

## What you still own

This is OSS infrastructure, not a managed service. Self-hosting means **you bring**:

- Instagram accounts (and the operational headache of keeping them un-banned)
- Residential or mobile proxies (Instagram's anti-abuse system flags datacenter IPs hard)
- Session storage and rotation
- Retry logic when challenges fire mid-script

If those line items sound like work you don't want, the same team behind `instagrapi` runs **[HikerAPI](https://hikerapi.com/p/7RAo9ACK)** as a managed equivalent — same Instagram surface, sessions and proxies handled on our side, called over HTTPS with an API key. It exists precisely because self-hosting `aiograpi-rest` has real ops cost. Use whichever fits — both paths are first-class.

## 30-second quick start

The API version is declared once in `pyproject.toml` and exposed through
`/build` and `/openapi.json`. The API keeps route semantics intentionally strict:
`GET` for reads/downloads, `POST` for login and creates/uploads, `PATCH` for
state changes, and `DELETE` for removals or state reversal. Undo-style paths
such as `/media/unlike`, `/user/unfollow`, and `/media/unarchive` were removed
before the public API became widely used; use `DELETE /media/like`,
`DELETE /user/follow`, and `DELETE /media/archive`.

```bash
docker run --rm -p 8000:8000 subzeroid/aiograpi-rest
```

Get a session id:

```bash
SESSIONID=$(curl -fsS -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=<USERNAME>&password=<PASSWORD>")
```

If you already have an Instagram `sessionid` cookie, import it with
`POST /auth/login/by/sessionid` instead of logging in with username/password.
It accepts the same `proxy`, `locale`, and `timezone` client options as
`POST /auth/login`.

Proxy, locale, and timezone can be set during login, session import, or patched later:

```bash
curl -fsS -X PATCH http://localhost:8000/auth/settings \
  -H "X-Session-ID: $SESSIONID" \
  -d "proxy=http://user:pass@host:port&locale=en_US&timezone=10800"
```

Open http://localhost:8000/docs for the live OpenAPI / Swagger UI. Click
**Authorize**, paste the returned session id once, and call protected routes
without adding `sessionid` to each request.

Fetch Instagram's public profile and about data over the same authorized
session:

```bash
curl "http://localhost:8000/user?username=instagram" \
  -H "X-Session-ID: $SESSIONID"

curl "http://localhost:8000/user/about?user_id=25025320" \
  -H "X-Session-ID: $SESSIONID"
```

Large read lists are paginated with the same response shape:
`{"items":[...],"next_cursor":"..."}`. Keep `next_cursor` and pass it as
`cursor` on the next request:

```bash
curl "http://localhost:8000/user/followers?user_id=25025320&amount=50" \
  -H "X-Session-ID: $SESSIONID"

curl "http://localhost:8000/user/posts?username=instagram&amount=12" \
  -H "X-Session-ID: $SESSIONID"

curl "http://localhost:8000/media/comments?media_id=MEDIA_ID&amount=20" \
  -H "X-Session-ID: $SESSIONID"
```

User post collection routes such as `/user/posts`, `/user/reels`,
`/user/videos`, and `/user/tagged/posts` accept either `user_id` or
`username`.

Search routes live under `/search` for users, accounts, followers/following,
hashtags, music, places, top results, Reels, recent searches, and typeahead:

```bash
curl "http://localhost:8000/search/hashtags?query=python" \
  -H "X-Session-ID: $SESSIONID"

curl "http://localhost:8000/search/followers?user_id=25025320&query=meta" \
  -H "X-Session-ID: $SESSIONID"
```

Story upload decoration fields are form fields. For mentions, pass JSON as a
form value. If `x`, `y`, `width`, `height`, or `rotation` are omitted for a
mention, location, or hashtag, the service applies a centered default position
before calling `aiograpi`:

```bash
curl -X POST "http://localhost:8000/story/upload/by/url" \
  -H "X-Session-ID: $SESSIONID" \
  -d "url=https://example.com/story.jpg" \
  --data-urlencode 'mentions=[{"user":{"pk":"25025320"}}]'
```

Feed upload and edit metadata works the same way. On `/photo/upload`,
`/video/upload`, `/clip/upload`, `/igtv/upload`, `/album/upload`, and
`PATCH /media`, pass `usertags` as JSON-encoded `Usertag` objects and
`location` as one JSON-encoded `Location` object. Empty metadata fields are
ignored.

```bash
curl -X POST "http://localhost:8000/photo/upload" \
  -H "X-Session-ID: $SESSIONID" \
  -F "file=@photo.jpeg;type=image/jpeg" \
  -F "caption=hello" \
  --form-string 'location={"pk":"1","name":"Place","lat":10.0,"lng":20.0}' \
  --form-string 'usertags=[{"user":{"pk":"25025320"},"x":0.5,"y":0.5}]'
```

Legacy `sessionid` query/form parameters are still accepted for existing
clients, but new integrations should use `X-Session-ID`.

Release artifacts are published from GitHub Actions: Docker images go to Docker
Hub and GHCR, Python packages go to PyPI through Trusted Publisher.

## Calling it from your language

The service is plain HTTP + JSON, so any HTTP client in any language works. Below are the shortest possible call snippets for the most common stacks; minimal example clients live in [`./golang`](golang) and [`./swift`](swift). They are integration examples, not generated SDKs.

Reusable quickstart examples show the full session flow; see
[`examples/README.md`](examples/README.md) for runnable commands:

- [`examples/curl/user-about.sh`](examples/curl/user-about.sh) for shell/curl
- [`examples/python/user_about.py`](examples/python/user_about.py) for Python without extra dependencies
- [`examples/typescript/user-about.ts`](examples/typescript/user-about.ts) for Node.js / TypeScript

Each example accepts `AIOGRAPI_REST_SESSIONID`, can import an Instagram cookie
through `POST /auth/login/by/sessionid`, can create a new session through
`POST /auth/login`, then calls `GET /user/about` with `X-Session-ID`.

**Node.js / TypeScript:**

```js
const r = await fetch("http://localhost:8000/user?username=instagram", {
  headers: { "X-Session-ID": SID },
});
const user = await r.json();
console.log(user.full_name, user.follower_count);
```

**Go** (full example: [`golang/client.go`](golang/client.go)):

```go
req, _ := http.NewRequest("GET", "http://localhost:8000/user?username=instagram", nil)
req.Header.Set("X-Session-ID", sid)
resp, _ := http.DefaultClient.Do(req)
defer resp.Body.Close()
var user map[string]any
json.NewDecoder(resp.Body).Decode(&user)
```

**PHP:**

```php
$ctx = stream_context_create(["http" => ["header" => "X-Session-ID: $sid\r\n"]]);
$user = json_decode(file_get_contents(
  "http://localhost:8000/user?username=instagram",
  false,
  $ctx
), true);
```

**Java** (with `java.net.http.HttpClient`):

```java
HttpResponse<String> r = HttpClient.newHttpClient().send(
  HttpRequest.newBuilder(URI.create("http://localhost:8000/user?username=instagram"))
    .header("X-Session-ID", sid)
    .build(),
  HttpResponse.BodyHandlers.ofString());
```

**Ruby:**

```ruby
require "net/http"; require "json"
uri = URI("http://localhost:8000/user?username=instagram")
req = Net::HTTP::Get.new(uri); req["X-Session-ID"] = sid
user = JSON.parse(Net::HTTP.start(uri.hostname, uri.port) { |http| http.request(req) }.body)
```

**Swift** (full example: [`swift/client.swift`](swift/client.swift)).

For typed client generation in C++, C#, F#, D, Erlang, Elixir, Nim, Haskell, Lisp, Clojure, Julia, R, Kotlin, Scala, OCaml, Crystal, Rust, Objective-C, Visual Basic, .NET, Pascal, Perl, Lua and others, see [Client Generation](docs/client-generation.md).

## Features

1. **Authorization** — login, 2FA, settings management
2. **Account** — account info, profile, profile picture, privacy
3. **Media** — info, paginated comments, likes, saves, pins, archive, edit, delete
4. **Direct** — inbox, threads, messages, seen state
5. **Discovery** — user, account, follower, following, hashtag, music, place,
   top, Reel, recent, and typeahead search; related hashtags, hashtag Reels,
   location guides, pinned posts, friendship, blocks, follow requests
6. **Video / Photo / IGTV / Reels / Album** — upload to feed and story, download
7. **Story / Highlights / Notes** — archive, viewers, highlights, notes
8. **Notifications / Insights** — inbox, notification settings, media and account insights

## Installation

Requires Python 3.13 for local installs. Dependencies are declared in
`pyproject.toml`; the legacy `requirements.txt` is intentionally gone. The
Docker image is the recommended runtime because it ships the same package layout
and entrypoint used in CI and release smoke tests.

Run the prebuilt Docker image:

```
docker run -p 8000:8000 subzeroid/aiograpi-rest
```

For a foreground one-off run that exits cleanly with Ctrl-C:

```
docker run --rm -p 8000:8000 subzeroid/aiograpi-rest
```

Images are published automatically from GitHub releases and semver tags to
Docker Hub and GitHub Packages. An `X.Y.Z` tag publishes
`subzeroid/aiograpi-rest:X.Y.Z`, `:X.Y`, `:latest`, and the matching
`ghcr.io/subzeroid/aiograpi-rest` tags.

PyPI and GitHub Release artifacts are published from the same tag workflow,
including the built wheel, source distribution, and `openapi.json`.

GitHub Packages image:

```
docker run -p 8000:8000 ghcr.io/subzeroid/aiograpi-rest
```

Or clone and build locally:

```
git clone https://github.com/subzeroid/aiograpi-rest.git
cd aiograpi-rest
docker build -t aiograpi-rest .
docker run -p 8000:8000 aiograpi-rest
```

Or use Docker Compose (recommended for local dev):

```
docker compose up api
```

Or run without Docker (requires Python 3.13):

```
python3.13 -m venv .venv
. .venv/bin/activate
python3.13 -m pip install -U pip
python3.13 -m pip install -e ".[test]"
uvicorn aiograpi_rest.main:app --host 0.0.0.0 --port 8000 --reload
```

## Usage

Live API documentation at http://localhost:8000/docs (Swagger UI):

![Swagger UI](docs/assets/swagger.png)

Project documentation is built with MkDocs and published to GitHub Pages:
https://subzeroid.github.io/aiograpi-rest/

The generated [aiograpi method coverage report](docs/aiograpi-coverage.md)
answers whether REST routes cover every `aiograpi.Client` method. They do not:
`aiograpi-rest` exposes a focused subset and documents the uncovered methods.

### Get a session id

```
curl -X 'POST' \
  'http://localhost:8000/auth/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=<USERNAME>&password=<PASSWORD>&verification_code=<2FA CODE>'
```

### Resolve a checkpoint challenge

When Instagram asks for an SMS or email checkpoint code, send the challenge
payload and code to the resolver. The service passes the code to `aiograpi`
without waiting for server stdin.

```
curl -X 'POST' \
  'http://localhost:8000/auth/challenge/resolve' \
  -H 'accept: application/json' \
  -H 'X-Session-ID: <SESSIONID>' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'last_json={"challenge":{"api_path":"/challenge/<USER_ID>/<NONCE>/"}}' \
  -d 'security_code=<SMS_OR_EMAIL_CODE>'
```

### Upload photo

```
curl -X 'POST' \
  'http://localhost:8000/story/upload' \
  -H 'accept: application/json' \
  -H 'X-Session-ID: <SESSIONID>' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@photo.jpeg;type=image/jpeg'
```

### Upload photo by URL

```
curl -X 'POST' \
  'http://localhost:8000/story/upload/by/url' \
  -H 'accept: application/json' \
  -H 'X-Session-ID: <SESSIONID>' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'url=https%3A%2F%2Fapi.telegram.org%2Ffile%2Ftest.jpg'
```

### Upload video

```
curl -X 'POST' \
  'http://localhost:8000/story/upload' \
  -H 'accept: application/json' \
  -H 'X-Session-ID: <SESSIONID>' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@video.mp4;type=video/mp4'
```

### Upload video by URL

```
curl -X 'POST' \
  'http://localhost:8000/story/upload/by/url' \
  -H 'accept: application/json' \
  -H 'X-Session-ID: <SESSIONID>' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'url=https%3A%2F%2Fapi.telegram.org%2Ffile%2Ftest.MP4'
```

## Generating client code

The service exposes an OpenAPI spec at `/openapi.json`. Use [`@openapitools/openapi-generator-cli`](https://www.npmjs.com/package/@openapitools/openapi-generator-cli) to generate a typed client in any supported language.

```
npx --yes @openapitools/openapi-generator-cli generate \
  -g <language> \
  -i http://localhost:8000/openapi.json \
  -o generated-clients/<language> \
  --skip-validate-spec
```

If your local Node/npm wrapper fails, use Docker:

```
curl -fsS http://localhost:8000/openapi.json -o openapi.json
docker run --rm -v "$PWD:/local" openapitools/openapi-generator-cli:v7.22.0 generate \
  -g <language> \
  -i /local/openapi.json \
  -o /local/generated-clients/<language> \
  --skip-validate-spec
```

`--skip-validate-spec` is sometimes needed for transient validator errors.
See [Client Generation](docs/client-generation.md) for Swift, Go, TypeScript, Python, PHP, Rust, Kotlin, Scala, C#, C++, and other OpenAPI Generator targets.

## Operating in production

When you start running this against a real Instagram surface — daily monitoring, multi-account orchestration, anything beyond ad-hoc — you will hit the same friction the Python world hits with `instagrapi` directly:

- **Account bans** — Instagram rotates abuse-detection rules; accounts that scraped fine last week get flagged this week.
- **Proxy hunting** — datacenter IPs are flagged on first contact; you need residential or mobile proxies, and you need to rotate them.
- **Sessions** — losing a session means re-logging in, which means the `challenge_required` cycle, which means manual SMS / email retrieval.

`aiograpi-rest` does not solve any of this — it just gives you HTTP access to the same library that hits the same wall. The honest options when you reach this point are:

1. **Build the ops layer yourself** — proxy pool, account warming, challenge-handler workers. This is real engineering, measured in weeks.
2. **Use [HikerAPI](https://hikerapi.com/p/7RAo9ACK)** — same Instagram surface as a managed HTTPS endpoint with an API key. Proxies and sessions handled on our side. The two products coexist deliberately: this repo is the OSS path; HikerAPI is the managed path. Pick whichever matches the cost shape you want.

## Related

- [`subzeroid/instagrapi`](https://github.com/subzeroid/instagrapi) — the underlying Python library
- [`subzeroid/aiograpi`](https://github.com/subzeroid/aiograpi) — async fork of `instagrapi`
- [`subzeroid/hikerapi-mcp`](https://github.com/subzeroid/hikerapi-mcp) — MCP server for HikerAPI (LLM tool surface)
- [instagrapi.com](https://instagrapi.com) — guides, integration recipes, error reference
- [HikerAPI](https://hikerapi.com/p/7RAo9ACK) — managed Instagram API
- [LamaTok](https://lamatok.com/p/43zuPqyT) — managed TikTok API
- [DataLikers](https://datalikers.com/p/S9Lv5vBy) — Instagram + TikTok cached datasets

## Testing

The offline test suite lives under `tests/` and runs with `pytest`.

Run all tests through Docker Compose:

```
docker compose run --rm test pytest --cov=. --cov-report=term-missing --cov-fail-under=100
```

A single test file:

```
docker compose run --rm test pytest tests/test_app_system.py
```

Locally (Python 3.13):

```
python3.13 -m pytest --cov=. --cov-report=term-missing --cov-fail-under=100
```

Optional live smoke tests against real Instagram accounts are gated by the `TEST_ACCOUNTS_URL` environment variable and are skipped by default:

```
TEST_ACCOUNTS_URL="https://example.com/accounts" python3.13 -m pytest tests/live -m live -o addopts='' -v
```

GitHub Actions also has a scheduled **Live Tests** workflow that runs nightly
and can be launched manually. It starts the Docker Compose API service, creates
a real session from `TEST_ACCOUNTS_URL`, sends it through `X-Session-ID`, and
checks `/user/about`, `/media/comments`, and paginated read-list routes. A
second nightly job runs the same HTTP smoke against the published Docker image
`subzeroid/aiograpi-rest:latest`, so the public `docker run` path is exercised
with a real session too. Both the direct ASGI live smoke and the published
image HTTP smoke upload a real JPEG to `/story/upload`, verify the created
story through `/story`, `/user/stories`, and `/story/viewers`, download the
media through `/story/download`, validate that it is an image, and delete the
story.

Generate and validate docs:

```
python3.13 scripts/generate_aiograpi_coverage.py
mkdocs build --strict
```

## Development

Runtime code lives under the `aiograpi_rest/` package:

- `aiograpi_rest/main.py` creates the FastAPI app, OpenAPI metadata, and system
  endpoints.
- `aiograpi_rest/routers/` contains route modules grouped by Instagram surface.
- `aiograpi_rest/dependencies.py`, `helpers.py`, and `storages.py` contain
  shared dependency injection, upload helpers, and session storage.

For debugging with the dev server bound:

```
docker compose run --service-ports api
```
