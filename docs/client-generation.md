# Client Generation

`aiograpi-rest` exposes an OpenAPI schema at `/openapi.json`. Generated
clients are a good fit when you want typed request and response models without
maintaining hand-written SDKs for every language.

The generated client is only as stable as the OpenAPI schema it was generated
from. Regenerate it when you upgrade `aiograpi-rest`, especially after endpoint,
request body, response model, or auth changes.

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

## Authentication

Generated clients should send the saved aiograpi-rest session in the
`X-Session-ID` header. Create it with `POST /auth/login` or
`POST /auth/login/by/sessionid`, then attach the returned `sessionid` to
subsequent requests.

How to set a default header depends on the generated language target. If the
generated SDK makes default headers awkward, keep the generated models and wrap
calls with your normal HTTP client.

## Repository Policy

The `golang/` and `swift/` directories in this repository are minimal
integration examples, not generated SDKs. Generated clients should usually live
in your application repository or in separate language-specific packages.
