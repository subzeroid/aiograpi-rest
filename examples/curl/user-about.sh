#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${AIOGRAPI_REST_BASE_URL:-http://localhost:8000}"
USER_ID="${AIOGRAPI_REST_USER_ID:-25025320}"

json_string_value() {
  python3 -c 'import json, sys; value = json.load(sys.stdin); print(value if isinstance(value, str) else "")'
}

sessionid="${AIOGRAPI_REST_SESSIONID:-}"

if [[ -z "$sessionid" && -n "${AIOGRAPI_REST_INSTAGRAM_SESSIONID:-}" ]]; then
  sessionid="$(
    curl -fsS -X POST "$BASE_URL/auth/login/by/sessionid" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      --data-urlencode "sessionid=$AIOGRAPI_REST_INSTAGRAM_SESSIONID" \
      | json_string_value
  )"
fi

if [[ -z "$sessionid" && -n "${AIOGRAPI_REST_USERNAME:-}" && -n "${AIOGRAPI_REST_PASSWORD:-}" ]]; then
  login_args=(
    --data-urlencode "username=$AIOGRAPI_REST_USERNAME"
    --data-urlencode "password=$AIOGRAPI_REST_PASSWORD"
  )
  if [[ -n "${AIOGRAPI_REST_VERIFICATION_CODE:-}" ]]; then
    login_args+=(--data-urlencode "verification_code=$AIOGRAPI_REST_VERIFICATION_CODE")
  fi
  sessionid="$(
    curl -fsS -X POST "$BASE_URL/auth/login" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      "${login_args[@]}" \
      | json_string_value
  )"
fi

if [[ -z "$sessionid" ]]; then
  echo "Set AIOGRAPI_REST_SESSIONID, AIOGRAPI_REST_INSTAGRAM_SESSIONID, or AIOGRAPI_REST_USERNAME/AIOGRAPI_REST_PASSWORD." >&2
  exit 1
fi

curl -fsS "$BASE_URL/user/about?user_id=$USER_ID" \
  -H "X-Session-ID: $sessionid"
