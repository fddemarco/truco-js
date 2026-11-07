"""Write the OpenAPI schema to frontend/openapi.json without starting a server."""

import json
import sys
from pathlib import Path

from app.main import app

DEFAULT = Path(__file__).parents[2] / "frontend" / "openapi.json"
out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
out.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(f"Wrote {out}")
