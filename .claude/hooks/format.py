#!/usr/bin/env python3
"""PostToolUse hook: auto-format the file Claude just edited.

- backend/**/*.py      -> ruff (import sort + format)
- frontend/** (web)    -> prettier

Never blocks the edit: formatter failures or missing tools exit 0 silently.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PRETTIER_EXTS = {".ts", ".js", ".mjs", ".vue", ".svelte", ".css", ".json", ".html", ".md"}


def run(cmd: list[str], cwd: Path) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not file_path:
        return

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".").resolve()
    path = Path(file_path).resolve()
    try:
        rel = path.relative_to(root)
    except ValueError:
        return
    if not path.is_file() or not rel.parts:
        return

    top = rel.parts[0]
    if top == "backend" and path.suffix == ".py" and shutil.which("uv"):
        backend = root / "backend"
        run(["uv", "run", "--quiet", "ruff", "check", "--fix", "--select", "I", str(path)], backend)
        run(["uv", "run", "--quiet", "ruff", "format", str(path)], backend)
    elif top == "frontend" and path.suffix in PRETTIER_EXTS:
        frontend = root / "frontend"
        if (frontend / "node_modules" / ".bin" / "prettier").exists():
            run([str(frontend / "node_modules" / ".bin" / "prettier"), "--write", str(path)], frontend)


if __name__ == "__main__":
    main()
