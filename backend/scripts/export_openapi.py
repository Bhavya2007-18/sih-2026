"""Export frozen OpenAPI schema for Maya backend to openapi.json."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.main import app


def export_openapi() -> None:
    schema = app.openapi()
    root_dir = Path(__file__).parents[2]
    backend_dir = Path(__file__).parents[1]

    root_path = root_dir / "openapi.json"
    backend_path = backend_dir / "openapi.json"

    content = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
    root_path.write_text(content, encoding="utf-8")
    backend_path.write_text(content, encoding="utf-8")
    print(f"Exported openapi.json to {root_path} and {backend_path}")


if __name__ == "__main__":
    export_openapi()
