"""Persistent client state (device identity, sessions, preferences).

Stored as JSON under the platform data dir
(``%LOCALAPPDATA%\\gpcli\\state.json`` on Windows). State written by the
pre-rename ``mygp-cli`` builds is migrated automatically on first load.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import platformdirs
from pydantic import BaseModel, Field

from gpcli.constants import APP_NAME
from gpcli.models import Auth, GuestSession

_LEGACY_APP_NAME = "mygp-cli"  # pre-rename state directory


def state_path() -> Path:
    return Path(platformdirs.user_data_dir(APP_NAME, appauthor=False)) / "state.json"


def _legacy_state_path() -> Path:
    return Path(platformdirs.user_data_dir(_LEGACY_APP_NAME, appauthor=False)) / "state.json"


class DeviceIdentity(BaseModel):
    """The emulated Android device — `X-REFERENCE-ID` is the Android ID."""

    device_id: str  # 16 lowercase hex chars, like Settings.Secure.ANDROID_ID
    device_model: str = "Pixel 8"  # Build.MODEL
    device_name: str = "Google"  # Build.MANUFACTURER


class State(BaseModel):
    """Root state object. Knows how to persist itself."""

    model_config = {"validate_assignment": True}

    device: DeviceIdentity
    language: str = "en"
    auth: Auth | None = None
    staged_msisdn: str | None = None  # OTP in flight (login -> verify)
    guest: GuestSession | None = None
    path: Path = Field(default_factory=state_path, exclude=True)

    @property
    def has_subscriber(self) -> bool:
        return bool(self.auth and self.auth.access_token)

    @property
    def ng(self) -> str:
        return str(self.auth.ng) if self.auth else "0"

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return self.path


def _new_device_id() -> str:
    return "".join(random.choices("0123456789abcdef", k=16))


def load_state(path: Path | None = None) -> State:
    explicit = path is not None
    path = path or state_path()
    if path.exists():
        try:
            state = State.model_validate(json.loads(path.read_text(encoding="utf-8")))
            state.path = path
            return state
        except Exception:
            pass  # corrupt state — start fresh rather than crash
    if not explicit:
        # one-time migration from the pre-rename mygp-cli directory (default
        # location only — explicit paths are caller-managed)
        legacy = _legacy_state_path()
        if legacy.exists():
            try:
                state = State.model_validate(json.loads(legacy.read_text(encoding="utf-8")))
                state.path = path
                state.save()
                return state
            except Exception:
                pass
    return State(device=DeviceIdentity(device_id=_new_device_id()), path=path)


def apply_new_auth(state: State, auth: Auth) -> Auth:
    """Stamp client-side bookkeeping and promote to active session."""
    auth.created_at = int(time.time())
    if not auth.token and auth.access_token:
        auth.token = auth.access_token
    state.auth = auth
    return auth
