"""Welcome Tune service.

Wire format (verified against the decompiled sources): ``GET /wt/status`` -> {status: <int>};
``GET /wt/list`` -> [WelcomeTune]; ``POST /wt/search {keyword}``;
``POST /wt/add {tone_code, connection_type}``;
``POST /v2/wt/activate {characteristic: [{name, value}…], reference_id}``;
``POST /v2/wt/deactivate {connection_type}``.
"""

from __future__ import annotations

import uuid

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import WelcomeTune

WT_STATUS_ENDPOINT = "/wt/status"
WT_LIST_ENDPOINT = "/wt/list"
WT_SEARCH_ENDPOINT = "/wt/search"
WT_ADD_ENDPOINT = "/wt/add"
WT_ACTIVATE_V2_ENDPOINT = "/v2/wt/activate"
WT_DEACTIVATE_V2_ENDPOINT = "/v2/wt/deactivate"


class WelcomeTuneService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def status(self) -> dict:
        return self.client.get_json("GET", WT_STATUS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)

    def tunes(self) -> list[WelcomeTune]:
        data = self.client.get_json("GET", WT_LIST_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        items = data if isinstance(data, list) else []
        return [WelcomeTune.model_validate(item) for item in items if isinstance(item, dict)]

    def search(self, keyword: str) -> list[WelcomeTune]:
        data = self.client.get_json(
            "POST", WT_SEARCH_ENDPOINT,
            json_body={"keyword": keyword},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        tunes = data.get("tuneList", []) if isinstance(data, dict) else []
        return [WelcomeTune.model_validate(item) for item in tunes if isinstance(item, dict)]

    def connection_type(self) -> str:
        auth = self.client.state.auth
        return (auth and getattr(auth, "type", None)) or "prepaid"

    def add(self, tone_code: str) -> dict:
        """`POST /wt/add {tone_code, connection_type}` — buy a tune."""
        return self.client.get_json(
            "POST", WT_ADD_ENDPOINT,
            json_body={"tone_code": tone_code, "connection_type": self.connection_type()},
            auth_mode=AuthMode.SUBSCRIBER,
        )

    def activate(self, tone_code: str) -> dict:
        """v2 SDK flow: characteristics array + reference id."""
        return self.client.get_json(
            "POST", WT_ACTIVATE_V2_ENDPOINT,
            json_body={
                "characteristic": [{"name": "tone_code", "value": tone_code}],
                "reference_id": uuid.uuid4().hex,
            },
            auth_mode=AuthMode.SUBSCRIBER,
        )

    def deactivate(self) -> dict:
        return self.client.get_json(
            "POST", WT_DEACTIVATE_V2_ENDPOINT,
            json_body={"connection_type": self.connection_type()},
            auth_mode=AuthMode.SUBSCRIBER,
        )
