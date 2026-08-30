"""Shared fixtures — hermetic state, scripted mock transport."""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest
from constants import AUTH_ID, DEVICE_ID, DEVICE_MANUFACTURER, DEVICE_MODEL, MSISDN_880

from gpcli.client import MyGPClient
from gpcli.state import State


@pytest.fixture()
def state(tmp_path) -> State:
    """State pointed at a temp file, with a logged-in subscriber session."""
    now = int(time.time())
    s = State.model_validate({
        "device": {"device_id": DEVICE_ID, "device_model": DEVICE_MODEL,
                   "device_name": DEVICE_MANUFACTURER},
        "language": "en",
        "auth": {
            "id": AUTH_ID,
            "access_token": "TOKEN-A",
            "refresh_token": "REFRESH-A",
            "msisdn": MSISDN_880,
            "expire_at": now + 3600,
            "created_at": now - 1200,
            "is_primary": 1,
            "ng": 0,
        },
    })
    s.path = tmp_path / "state.json"
    return s


@pytest.fixture()
def make_client(state):
    """Client factory over a scripted MockTransport; records requests."""

    class Recorder:
        def __init__(self):
            self.requests: list[httpx.Request] = []
            self.routes: list[tuple[str, str, dict[str, Any]]] = []

        def add(self, method: str, url_part: str, **response_kwargs: Any) -> None:
            self.routes.append((method.upper(), url_part, response_kwargs))

        def handler(self, request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            for i, (method, url_part, kwargs) in enumerate(self.routes):
                if request.method == method and url_part in str(request.url):
                    self.routes.pop(i)  # one-shot: retries see the next matching route
                    kwargs.setdefault("status_code", 200)
                    return httpx.Response(**kwargs)
            return httpx.Response(404, text=f"no route for {request.method} {request.url}")

    def factory() -> tuple[MyGPClient, Recorder]:
        recorder = Recorder()
        client = MyGPClient(state, transport=httpx.MockTransport(recorder.handler))
        return client, recorder

    return factory
