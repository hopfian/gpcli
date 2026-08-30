"""Missed Call Alert service.

Wire format (verified against the decompiled sources): ``GET /mca`` -> {status: "1"|"0",
due_date, message}; ``POST /mca {status: true|false}`` ->
{status: "pending"|...}.
"""

from __future__ import annotations

from gpcli.client import ApiCaller, AuthMode

MCA_ENDPOINT = "/mca"


class McaService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def status(self) -> dict:
        return self.client.get_json("GET", MCA_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)

    def set(self, enabled: bool) -> dict:
        """`{"status": true|false}` — "pending" means the server accepted."""
        return self.client.get_json(
            "POST", MCA_ENDPOINT,
            json_body={"status": enabled},
            auth_mode=AuthMode.SUBSCRIBER,
        )
