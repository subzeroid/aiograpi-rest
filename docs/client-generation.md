# Client Generation

`aiograpi-rest` exposes an OpenAPI schema at `/openapi.json`. Generated
clients are a good fit when you want typed request and response models without
maintaining hand-written SDKs for every language.

The generated client is only as stable as the OpenAPI schema it was generated
from. Regenerate it when you upgrade `aiograpi-rest`, especially after endpoint,
request body, response model, or auth changes.

## OpenAPI 3.0.3 compatibility

`aiograpi-rest` publishes OpenAPI 3.0.3 for generator compatibility. FastAPI and
Pydantic can emit OpenAPI 3.1-style nullable schemas internally, but the exported
schema is normalized back to 3.0.3-compatible `nullable: true` fields before it
is served from `/openapi.json` or attached to a release.

Request and response schemas are also renamed to stable operation-based names
such as `AuthLoginRequest` and `AuthLoginResponse`. This keeps generated SDKs
from exposing framework-generated names like `Body_*` or inline `Response *`
models.

## Start The API

Run the same server version that your application will call:

```bash
docker run --rm -p 8000:8000 subzeroid/aiograpi-rest
```

Set the schema URL once:

```bash
export AIOGRAPI_REST_OPENAPI_URL=http://localhost:8000/openapi.json
mkdir -p generated-clients
```

The commands below use the npm wrapper for OpenAPI Generator:

```bash
npx --yes @openapitools/openapi-generator-cli version
```

The npm wrapper may create `openapitools.json` in your current directory. Keep
it in your application repository if you want repeatable generator output.

For repeated generation, define this helper once in your shell:

```bash
generate_aiograpi_rest_client() {
  local generator="$1"
  local output="$2"
  shift 2

  npx --yes @openapitools/openapi-generator-cli generate \
    -i "$AIOGRAPI_REST_OPENAPI_URL" \
    -g "$generator" \
    -o "generated-clients/$output" \
    --skip-validate-spec \
    "$@"
}
```

## TypeScript

```bash
npx --yes @openapitools/openapi-generator-cli generate \
  -i "$AIOGRAPI_REST_OPENAPI_URL" \
  -g typescript-fetch \
  -o generated-clients/typescript-fetch \
  --skip-validate-spec \
  --additional-properties=npmName=aiograpi-rest-client,supportsES6=true
```

## Python

```bash
npx --yes @openapitools/openapi-generator-cli generate \
  -i "$AIOGRAPI_REST_OPENAPI_URL" \
  -g python \
  -o generated-clients/python \
  --skip-validate-spec \
  --additional-properties=packageName=aiograpi_rest_client,projectName=aiograpi-rest-client
```

## Go

```bash
npx --yes @openapitools/openapi-generator-cli generate \
  -i "$AIOGRAPI_REST_OPENAPI_URL" \
  -g go \
  -o generated-clients/go \
  --skip-validate-spec \
  --additional-properties=packageName=aiograpi_rest_client
```

## Swift

```bash
npx --yes @openapitools/openapi-generator-cli generate \
  -i "$AIOGRAPI_REST_OPENAPI_URL" \
  -g swift5 \
  -o generated-clients/swift \
  --skip-validate-spec \
  --additional-properties=projectName=AiograpiRestClient
```

## More Languages

The generator names below were checked against OpenAPI Generator CLI 7.22.0.
Run them after defining `generate_aiograpi_rest_client` above.

```bash
# C++
generate_aiograpi_rest_client cpp-restsdk cpp-restsdk

# C# / .NET
generate_aiograpi_rest_client csharp csharp \
  --additional-properties=packageName=AiograpiRest.Client

# F# and Visual Basic can consume the generated C#/.NET package.
generate_aiograpi_rest_client csharp dotnet \
  --additional-properties=packageName=AiograpiRest.Client

# Erlang
generate_aiograpi_rest_client erlang-client erlang

# Elixir
generate_aiograpi_rest_client elixir elixir

# Nim
generate_aiograpi_rest_client nim nim

# Haskell
generate_aiograpi_rest_client haskell-http-client haskell

# Clojure
generate_aiograpi_rest_client clojure clojure

# Julia
generate_aiograpi_rest_client julia-client julia

# R
generate_aiograpi_rest_client r r

# Kotlin
generate_aiograpi_rest_client kotlin kotlin \
  --additional-properties=packageName=com.aiograpirest.client

# Scala
generate_aiograpi_rest_client scala-sttp4 scala-sttp4

# OCaml
generate_aiograpi_rest_client ocaml ocaml

# Crystal
generate_aiograpi_rest_client crystal crystal

# Rust
generate_aiograpi_rest_client rust rust \
  --additional-properties=packageName=aiograpi_rest_client

# Objective-C
generate_aiograpi_rest_client objc objc

# Perl
generate_aiograpi_rest_client perl perl

# Lua
generate_aiograpi_rest_client lua lua

# PHP
generate_aiograpi_rest_client php php \
  --additional-properties=invokerPackage=AiograpiRestClient

# Java
generate_aiograpi_rest_client java java \
  --additional-properties=apiPackage=com.aiograpirest.client.api,modelPackage=com.aiograpirest.client.model

# JavaScript
generate_aiograpi_rest_client javascript javascript

# Ruby
generate_aiograpi_rest_client ruby ruby

# Dart
generate_aiograpi_rest_client dart dart

# C
generate_aiograpi_rest_client c c

# Bash
generate_aiograpi_rest_client bash bash

# PowerShell
generate_aiograpi_rest_client powershell powershell

# Postman collection
generate_aiograpi_rest_client postman-collection postman
```

C++ has several generator variants. `cpp-restsdk` is a reasonable default, but
OpenAPI Generator also exposes `cpp-qt-client`, `cpp-oatpp-client`, `cpp-tiny`,
and platform-specific options.

## Languages Without Dedicated Client Generators

OpenAPI Generator CLI 7.22.0 does not include dedicated general-purpose client
generators for D, Common Lisp, Pascal, or Visual Basic.

Practical options:

- Use raw HTTP with the `/openapi.json` schema as reference.
- Generate a `postman-collection` artifact for manual exploration.
- For Visual Basic or F#, generate the C#/.NET client and consume that package.
- Try another OpenAPI generator if your language ecosystem has a better fit.

## Authentication

Generated clients should send the saved aiograpi-rest session in the
`X-Session-ID` header. Create it with `POST /auth/login` or
`POST /auth/login/by/sessionid`, then attach the returned `sessionid` to
subsequent requests.

How to set a default header depends on the generated language target. If the
generated SDK makes default headers awkward, keep the generated models and wrap
calls with your normal HTTP client.

For a hand-written session flow before introducing a generated SDK, see:

- [examples/curl/user-about.sh](https://github.com/subzeroid/aiograpi-rest/blob/main/examples/curl/user-about.sh)
- [examples/python/user_about.py](https://github.com/subzeroid/aiograpi-rest/blob/main/examples/python/user_about.py)
- [examples/typescript/user-about.ts](https://github.com/subzeroid/aiograpi-rest/blob/main/examples/typescript/user-about.ts)

## CI Smoke Check

The repository runs `scripts/check_client_generation.py` in CI. The script
exports the current OpenAPI schema with `scripts/export_openapi.py` and
smoke-generates `python`, `typescript-fetch`, `go`, and `swift5` clients with
OpenAPI Generator 7.22.0. This does not turn those generated outputs into
supported SDK packages; it only verifies that the published schema remains
usable by the main documented generator targets.

## Repository Policy

The `golang/` and `swift/` directories in this repository are minimal
integration examples, not generated SDKs. Generated clients should usually live
in your application repository or in separate language-specific packages.
