"""Signed pickles: the game state the registry stores in the database (app/games/registry.py).

Unpickling runs code, so a row is unpickled only once its HMAC-SHA256 matches, under a key
the database doesn't hold. Write access to the database alone can't run code here.

The key is STATE_KEY, required with DATABASE_URL (a deploy). Without either (local SQLite),
DATA_DIR/state.key is made on first use. A new key drops the running games (their rows no
longer verify); games are short-lived, so that is the whole cost of rotating it.
"""

import hashlib
import hmac
import os
import pickle
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings

DIGEST_SIZE = hashlib.sha256().digest_size


class BadSignature(Exception):
    """A row this app didn't sign (or signed with another key)."""


def state_key() -> bytes:
    settings = get_settings()
    if settings.state_key:
        return settings.state_key.encode()
    if settings.database_url:
        raise RuntimeError("STATE_KEY must be set when DATABASE_URL is (see .env.example)")
    return _key_file(settings.data_dir / "state.key")


@lru_cache
def _key_file(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_bytes().strip()
    key = secrets.token_urlsafe(32).encode()
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key


def keyed_hash(value: str) -> str:
    """A stable, non-reversible name for `value` (a client address in the rate limits)."""
    return hmac.new(state_key(), value.encode(), "sha256").hexdigest()[:32]


def seal(obj: Any) -> bytes:
    data = pickle.dumps(obj)
    return hmac.digest(state_key(), data, "sha256") + data


def unseal(blob: bytes) -> Any:
    blob = bytes(blob)
    mac, data = blob[:DIGEST_SIZE], blob[DIGEST_SIZE:]
    if not hmac.compare_digest(mac, hmac.digest(state_key(), data, "sha256")):
        raise BadSignature("the stored state is not signed with STATE_KEY")
    return pickle.loads(data)
