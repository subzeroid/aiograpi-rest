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
