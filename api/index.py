"""Vercel entrypoint: every /api/* request is rewritten here (see vercel.json) and served by
the FastAPI app in backend/, which still sees the original path."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
