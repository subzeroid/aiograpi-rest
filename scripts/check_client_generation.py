#!/usr/bin/env python3
"""Smoke-generate OpenAPI clients for the primary documented targets."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PACKAGE = "@openapitools/openapi-generator-cli"
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


def generator_version() -> str:
    config = json.loads((ROOT / "openapitools.json").read_text())
    return config["generator-cli"]["version"]


def docker_image() -> str:
    return f"openapitools/openapi-generator-cli:v{generator_version()}"


def selected_targets() -> dict[str, list[str]]:
    raw = os.environ.get("AIOGRAPI_REST_CLIENT_GENERATORS", "").strip()
    if not raw:
        return DEFAULT_TARGETS
    names = [name.strip() for name in raw.split(",") if name.strip()]
    unknown = sorted(set(names) - set(DEFAULT_TARGETS))
    if unknown:
        raise SystemExit(f"Unknown client generator(s): {', '.join(unknown)}")
    return {name: DEFAULT_TARGETS[name] for name in names}


def run(command: list[str], cwd: Path = ROOT, *, print_on_error: bool = True) -> None:
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
        if print_on_error:
            print(result.stdout, end="")
        raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout)


def _docker_path(value: str, temp: Path) -> str:
    try:
        path = Path(value)
        relative = path.resolve().relative_to(temp.resolve())
    except (OSError, ValueError):
        return value
    return f"/local/{relative.as_posix()}"


def openapi_generator_command(args: list[str], *, backend: str, temp: Path) -> list[str]:
    if backend == "npx":
        return ["npx", "--yes", GENERATOR_PACKAGE, *args]
    if backend == "docker":
        return [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{temp}:/local",
            docker_image(),
            *[_docker_path(arg, temp) for arg in args],
        ]
    raise ValueError(f"Unknown OpenAPI Generator backend: {backend}")


def _require_backend(backend: str) -> None:
    executable = "npx" if backend == "npx" else "docker"
    if shutil.which(executable) is None:
        raise SystemExit(f"{executable} is required to run OpenAPI Generator with backend={backend}")


def smoke_generate_clients(openapi: Path, output_root: Path, temp: Path, backend: str, *, quiet_errors: bool = False) -> None:
    _require_backend(backend)
    print(f"Using OpenAPI Generator backend: {backend}", flush=True)
    run(
        openapi_generator_command(["validate", "-i", str(openapi)], backend=backend, temp=temp),
        print_on_error=not quiet_errors,
    )

    for generator, extra_args in selected_targets().items():
        output = output_root / generator
        run(
            openapi_generator_command(
                [
                    "generate",
                    "-i",
                    str(openapi),
                    "-g",
                    generator,
                    "-o",
                    str(output),
                    "--skip-validate-spec",
                    *extra_args,
                ],
                backend=backend,
                temp=temp,
            ),
            print_on_error=not quiet_errors,
        )
        validate_generated_names(generator, output)


def run_smoke_with_fallback(openapi: Path, output_root: Path, temp: Path, backend: str) -> None:
    if backend not in {"auto", "npx", "docker"}:
        raise SystemExit("AIOGRAPI_REST_OPENAPI_GENERATOR_BACKEND must be one of: auto, npx, docker")
    if backend in {"npx", "docker"}:
        smoke_generate_clients(openapi, output_root, temp, backend)
        return
    if shutil.which("npx") is None:
        smoke_generate_clients(openapi, output_root, temp, "docker")
        return

    try:
        smoke_generate_clients(openapi, output_root, temp, "npx", quiet_errors=True)
    except subprocess.CalledProcessError as exc:
        if shutil.which("docker") is None:
            raise
        detail = ""
        if exc.output:
            lines = [line.strip() for line in exc.output.splitlines() if line.strip()]
            if lines:
                detail = f" Last npx line: {lines[-1]}"
        print(f"npx OpenAPI Generator failed; falling back to Docker backend.{detail}", flush=True)
        if output_root.exists():
            shutil.rmtree(output_root)
        smoke_generate_clients(openapi, output_root, temp, "docker")


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
    with tempfile.TemporaryDirectory(prefix="aiograpi-rest-client-generation-") as temp_dir:
        temp = Path(temp_dir)
        openapi = temp / "openapi.json"
        output_root = temp / "clients"

        run([sys.executable, "scripts/export_openapi.py", str(openapi)])
        backend = os.environ.get("AIOGRAPI_REST_OPENAPI_GENERATOR_BACKEND", "auto").strip() or "auto"
        run_smoke_with_fallback(openapi, output_root, temp, backend)


if __name__ == "__main__":  # pragma: no cover
    main()
