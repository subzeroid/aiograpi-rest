# aiograpi-rest Examples

These examples use the same minimal session flow:

1. Reuse `AIOGRAPI_REST_SESSIONID` if you already have an aiograpi-rest session.
2. Import an Instagram `sessionid` cookie through `POST /auth/login/by/sessionid`
   when `AIOGRAPI_REST_INSTAGRAM_SESSIONID` is set.
3. Create a new session through `POST /auth/login` when
   `AIOGRAPI_REST_USERNAME` and `AIOGRAPI_REST_PASSWORD` are set.
4. Call `GET /user/about` with the saved session in `X-Session-ID`.

Start the API first:

```bash
docker run --rm -p 8000:8000 subzeroid/aiograpi-rest
```

Run the curl example:

```bash
AIOGRAPI_REST_SESSIONID="<SESSIONID>" ./examples/curl/user-about.sh
```

Run the Python example:

```bash
AIOGRAPI_REST_SESSIONID="<SESSIONID>" python3 examples/python/user_about.py
```

Run the TypeScript example with Node.js 18+:

```bash
AIOGRAPI_REST_SESSIONID="<SESSIONID>" npx --yes tsx examples/typescript/user-about.ts
```
