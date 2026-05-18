# aiograpi-rest Go Example

Minimal Go client example for calling an `aiograpi-rest` server over HTTP.
This is an integration example, not a generated OpenAPI SDK.

Start the API first:

```bash
docker run --rm -p 8000:8000 subzeroid/aiograpi-rest
```

## Build

```bash
go build client.go
```

## Launch

```bash
./client
```

To call authenticated endpoints, pass an existing aiograpi-rest session:

```bash
AIOGRAPI_REST_SESSIONID="<SESSIONID>" AIOGRAPI_REST_USER_ID="25025320" ./client
```

Or let the example create a session first:

```bash
AIOGRAPI_REST_USERNAME="<USERNAME>" AIOGRAPI_REST_PASSWORD="<PASSWORD>" ./client
```
