import json
import sys
from pathlib import Path

from aiograpi_rest.main import app


def export_openapi(output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    return output


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("Usage: export_openapi.py OUTPUT")
    export_openapi(args[0])


if __name__ == "__main__":  # pragma: no cover
    main()
