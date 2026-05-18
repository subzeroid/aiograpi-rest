# aiograpi-rest Swift Example

Minimal Swift client example for calling an `aiograpi-rest` server over HTTP.
This is an integration example, not a generated OpenAPI SDK.

Start the API first:

```bash
docker run --rm -p 8000:8000 subzeroid/aiograpi-rest
```

## Launch As Script

```bash
./client.swift
```

To call authenticated endpoints, pass an existing aiograpi-rest session:

```bash
AIOGRAPI_REST_SESSIONID="<SESSIONID>" AIOGRAPI_REST_USER_ID="25025320" ./client.swift
```

Or let the example create a session first:

```bash
AIOGRAPI_REST_USERNAME="<USERNAME>" AIOGRAPI_REST_PASSWORD="<PASSWORD>" ./client.swift
```

## Compile

```bash
swiftc client.swift -o client
```

or:

```bash
xcrun -sdk macosx swiftc client.swift -o client
```

## Launch Compiled Version

```bash
./client
```
