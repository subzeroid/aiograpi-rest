#!/usr/bin/env python3
"""Smoke-generate OpenAPI clients for the primary documented targets."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = {
    "python": [
        "--additional-properties=packageName=aiograpi_rest_client,projectName=aiograpi-rest-client",
    ],
    "typescript-fetch": [
        "--additional-properties=npmName=aiograpi-rest-client,supportsES6=true",
    ],
    "go": [
        "--additional-properties=packageName=aiograpi_rest_client",
    ],
    "swift5": [
        "--additional-properties=projectName=AiograpiRestClient",
    ],
}
GENERATED_NAME_CHECKS = {
    "python": (
        "aiograpi_rest_client/models/auth_login_response.py",
        "aiograpi_rest_client/models/auth_login_by_session_id_response.py",
    ),
    "typescript-fetch": (
        "src/models/AuthLoginResponse.ts",
        "src/models/AuthLoginBySessionIdResponse.ts",
    ),
    "go": (
        "model_auth_login_response.go",
        "model_auth_login_by_session_id_response.go",
    ),
    "swift5": (
        "AiograpiRestClient/Classes/OpenAPIs/Models/AuthLoginResponse.swift",
        "AiograpiRestClient/Classes/OpenAPIs/Models/AuthLoginBySessionIdResponse.swift",
    ),
}
UNSTABLE_GENERATED_NAMES = (
    "ResponsePostauthlogin",
    "ResponsePostauthloginbysessionid",
    "BodyPostauthlogin",
    "BodyPostauthloginbysessionid",
    "Response_Postauthlogin",
    "Response_Postauthloginbysessionid",
)


def selected_targets() -> dict[str, list[str]]:
    raw = os.environ.get("AIOGRAPI_REST_CLIENT_GENERATORS", "").strip()
    if not raw:
        return DEFAULT_TARGETS
    names = [name.strip() for name in raw.split(",") if name.strip()]
    unknown = sorted(set(names) - set(DEFAULT_TARGETS))
    if unknown:
        raise SystemExit(f"Unknown client generator(s): {', '.join(unknown)}")
    return {name: DEFAULT_TARGETS[name] for name in names}


def run(command: list[str], cwd: Path = ROOT) -> None:
    print("+", " ".join(command), flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        raise subprocess.CalledProcessError(result.returncode, command)


def validate_generated_names(generator: str, output: Path) -> None:
    for relative_path in GENERATED_NAME_CHECKS[generator]:
        expected = output / relative_path
        if not expected.exists():
            raise SystemExit(f"{generator} did not generate expected file: {relative_path}")

    for path in output.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(output).as_posix()
        if any(name in relative_path for name in UNSTABLE_GENERATED_NAMES):
            raise SystemExit(f"{generator} generated unstable file name: {relative_path}")
        if path.suffix.lower() not in {".go", ".md", ".py", ".swift", ".ts"}:
            continue
        text = path.read_text(errors="ignore")
        for name in UNSTABLE_GENERATED_NAMES:
            if name in text:
                raise SystemExit(f"{generator} generated unstable model name {name} in {relative_path}")


def main() -> None:
    if shutil.which("npx") is None:
        raise SystemExit("npx is required to run OpenAPI Generator")

    with tempfile.TemporaryDirectory(prefix="aiograpi-rest-client-generation-") as temp_dir:
        temp = Path(temp_dir)
        openapi = temp / "openapi.json"
        output_root = temp / "clients"

        run([sys.executable, "scripts/export_openapi.py", str(openapi)])
        run(["npx", "--yes", "@openapitools/openapi-generator-cli", "validate", "-i", str(openapi)])

        for generator, extra_args in selected_targets().items():
            output = output_root / generator
            run(
                [
                    "npx",
                    "--yes",
                    "@openapitools/openapi-generator-cli",
                    "generate",
                    "-i",
                    str(openapi),
                    "-g",
                    generator,
                    "-o",
                    str(output),
                    "--skip-validate-spec",
                    *extra_args,
                ]
            )
            validate_generated_names(generator, output)


if __name__ == "__main__":
    main()
