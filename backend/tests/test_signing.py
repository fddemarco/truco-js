"""Game state is signed with STATE_KEY: a deploy needs one, and locally a key is made once
and kept, so games survive restarts."""

import pytest

from app import signing
from app.config import get_settings
from app.main import create_app


def test_a_local_key_is_made_once_and_kept(data_dir):
    sealed = signing.seal({"a": 1})
    assert (data_dir / "state.key").exists()
    signing._key_file.cache_clear()  # a restart
    assert signing.unseal(sealed) == {"a": 1}


def test_another_key_rejects_the_state(data_dir, monkeypatch):
    sealed = signing.seal({"a": 1})
    monkeypatch.setenv("STATE_KEY", "k" * 32)
    get_settings.cache_clear()
    with pytest.raises(signing.BadSignature):
        signing.unseal(sealed)
    with pytest.raises(signing.BadSignature):
        signing.unseal(sealed[:-1] + b".")


def test_a_deploy_without_state_key_fails_at_startup(data_dir, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    monkeypatch.setenv("STATE_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="STATE_KEY"):
        create_app()


def test_a_short_state_key_is_refused(data_dir, monkeypatch):
    monkeypatch.setenv("STATE_KEY", "too-short")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="32 characters"):
        get_settings()
