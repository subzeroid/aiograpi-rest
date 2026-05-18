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


def main() -> None:
    if shutil.which("npx") is None:
        raise SystemExit("npx is required to run OpenAPI Generator")

    with tempfile.TemporaryDirectory(prefix="aiograpi-rest-client-generation-") as temp_dir:
        temp = Path(temp_dir)
        openapi = temp / "openapi.json"
        output_root = temp / "clients"

        run([sys.executable, "scripts/export_openapi.py", str(openapi)])

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


if __name__ == "__main__":
    main()
