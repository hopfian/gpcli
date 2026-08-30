"""State persistence and auth bookkeeping."""

import json
import time

from gpcli.models import Auth, GuestSession
from gpcli.state import apply_new_auth, load_state


def test_roundtrip(state):
    state.save()
    loaded = load_state(state.path)
    assert loaded.auth.access_token == "TOKEN-A"
    assert loaded.device.device_id == "0123456789abcdef"
    assert loaded.path == state.path


def test_load_missing_creates_fresh(tmp_path):
    s = load_state(tmp_path / "nope.json")
    assert s.auth is None
    assert len(s.device.device_id) == 16
    assert all(c in "0123456789abcdef" for c in s.device.device_id)


def test_load_corrupt_falls_back(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{ this is not json", encoding="utf-8")
    s = load_state(p)
    assert s.auth is None


def test_legacy_migration(tmp_path, monkeypatch):
    """Pre-rename mygp-cli state migrates to the default path on first load."""
    legacy = tmp_path / "legacy" / "state.json"
    legacy.parent.mkdir()
    legacy.write_text(json.dumps({
        "device": {"device_id": "0123456789abcdef", "device_model": "Pixel 8",
                   "device_name": "Google"},
        "auth": {"id": 100000001, "access_token": "TOKEN-A", "refresh_token": "REFRESH-A"},
    }), encoding="utf-8")
    target = tmp_path / "new" / "state.json"
    monkeypatch.setattr("gpcli.state.state_path", lambda: target)
    monkeypatch.setattr("gpcli.state._legacy_state_path", lambda: legacy)

    s = load_state()  # default-path resolution -> migration kicks in
    assert s.auth is not None and s.auth.access_token == "TOKEN-A"
    assert s.path == target
    assert target.exists()  # persisted to the new location

    # second load: the new file wins, no re-migration needed
    legacy.unlink()
    s2 = load_state()
    assert s2.auth is not None and s2.auth.access_token == "TOKEN-A"


def test_explicit_path_never_migrates(tmp_path, monkeypatch):
    """Explicit paths are caller-managed — legacy state must not leak in."""
    legacy = tmp_path / "legacy" / "state.json"
    legacy.parent.mkdir()
    legacy.write_text(json.dumps({
        "device": {"device_id": "0123456789abcdef", "device_model": "Pixel 8",
                   "device_name": "Google"},
        "auth": {"id": 100000001, "access_token": "TOKEN-A"},
    }), encoding="utf-8")
    monkeypatch.setattr("gpcli.state._legacy_state_path", lambda: legacy)

    s = load_state(tmp_path / "explicit.json")
    assert s.auth is None  # fresh state despite legacy file existing


def test_apply_new_auth_stamps_created_at(state):
    now = int(time.time())
    auth = Auth(id=1, access_token="N", refresh_token="R")
    apply_new_auth(state, auth)
    assert state.auth is auth
    assert abs(auth.created_at - now) <= 2
    assert auth.token == "N"  # token mirrors access_token


def test_guest_expiry_math():
    now = int(time.time())
    g = GuestSession(user_id="1", client_id="c", client_secret="s",
                     access_token="t", issued_at=now - 4000, expires_at=now + 300)
    assert not g.token_expired(now)
    assert g.token_expired(now + 1000)
    assert GuestSession(user_id="1", client_id="c", client_secret="s").token_expired(now)
