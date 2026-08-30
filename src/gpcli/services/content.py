"""Content endpoints — cards engine, districts, weather, news.

Cards/districts/weather ride the Apigee gateway with a guest-mode session
(validated path); news is a subscriber endpoint on the
legacy gateway.
"""

from __future__ import annotations

import time
from typing import Any

from gpcli.client import ApiCaller, AuthMode
from gpcli.constants import (
    CARDS_URL,
    DISTRICTS_URL,
    NEWS_ENDPOINT,
    WEATHER_URL,
)
from gpcli.services.auth import AuthService


class ContentService:
    def __init__(self, client: ApiCaller, auth_service: AuthService | None = None):
        self.client = client
        self._auth = auth_service or AuthService(client)

    def cards(self, *, category: str = "All", offset: int = 0, limit: int = 20) -> dict:
        """`GET apigw/mygp/v1/cards` — the remotely-configured homepage engine."""
        self._ensure_guest()
        return self.client.get_json(
            "GET", CARDS_URL,
            params={"category": category, "pageoffset": offset, "pagelimit": limit},
            auth_mode=AuthMode.GUEST,
        )

    def districts(self) -> list[str]:
        """`GET apigw/mygp/v1/districts`."""
        self._ensure_guest()
        data = self.client.get_json("GET", DISTRICTS_URL, auth_mode=AuthMode.GUEST)
        return data.get("data", []) if isinstance(data, dict) else []

    def weather(self, lat: str, lon: str) -> dict[str, Any]:
        """`GET apigw/mygp/v1/weather` (param contract partially verified)."""
        self._ensure_guest()
        return self.client.get_json(
            "GET", WEATHER_URL,
            params={"lat": lat, "lon": lon},
            auth_mode=AuthMode.GUEST,
        )

    def news(self) -> dict[str, Any]:
        """`GET /tps/v3/news` — subscriber-authenticated news feed."""
        return self.client.get_json("GET", NEWS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)

    def _ensure_guest(self) -> None:
        """Guest sessions expire hourly; re-mint transparently."""
        state = self.client.state
        if state.guest is None or state.guest.token_expired(int(time.time())):
            self._auth.guest_login(refresh_token=True)
