# Getting Started

## Run With Docker

```bash
docker run --rm -p 8000:8000 subzeroid/aiograpi-rest
```

Open <http://localhost:8000/docs> for Swagger UI.

For local development from a checkout:

```bash
docker compose up api
```

## Run Locally

```bash
python3.13 -m venv .venv
. .venv/bin/activate
python3.13 -m pip install -U pip
python3.13 -m pip install -e ".[test,docs]"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Create A Session

```bash
SESSIONID=$(curl -fsS -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=<USERNAME>&password=<PASSWORD>")
```

The response is the session ID. If you already have an Instagram `sessionid`
cookie, use `POST /auth/login/by/sessionid` instead.

To use a proxy from the start, pass it during login:

```bash
SESSIONID=$(curl -fsS -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=<USERNAME>&password=<PASSWORD>&proxy=http://user:pass@host:port")
```

To change runtime client options after login:

```bash
curl -fsS -X PATCH http://localhost:8000/auth/settings \
  -H "X-Session-ID: $SESSIONID" \
  -d "proxy=http://user:pass@new-host:port&locale=en_US&timezone=10800"
```

In Swagger UI, click **Authorize** and paste the session id once. For direct
HTTP calls, send it as `X-Session-ID`:

```bash
curl "http://localhost:8000/user/info/by/username?username=instagram" \
  -H "X-Session-ID: $SESSIONID"

curl "http://localhost:8000/user/about?user_id=25025320" \
  -H "X-Session-ID: $SESSIONID"
```

Older clients may still pass `sessionid` in query parameters or form data, but
new integrations should use `X-Session-ID`.

## Check The Service

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/deps
```
