"""FnF (Friends & Family) management.

Wire formats (verified against the decompiled sources):

* ``GET  /fnf-list``                      -> {normal_fnf[], super_fnf[], info}
* ``POST /fnf-add``    {fnf, is_super}     -> {status, remarks}   ("1"/"0")
* ``POST /fnf-delete`` {fnf, is_super}     -> {status, remarks}
  (deletion is locked until end-of-day of `changedate` + 30 days server-side)
"""

from __future__ import annotations

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import FnfList

FNF_LIST_ENDPOINT = "/fnf-list"
FNF_ADD_ENDPOINT = "/fnf-add"
FNF_DELETE_ENDPOINT = "/fnf-delete"


class FnfService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def list(self) -> FnfList:
        data = self.client.get_json("GET", FNF_LIST_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return FnfList.model_validate(data)

    def add(self, msisdn: str, *, super_fnf: bool = False) -> dict:
        return self.client.get_json(
            "POST", FNF_ADD_ENDPOINT,
            json_body={"fnf": msisdn, "is_super": "1" if super_fnf else "0"},
            auth_mode=AuthMode.SUBSCRIBER,
        )

    def remove(self, msisdn: str, *, super_fnf: bool = False) -> dict:
        return self.client.get_json(
            "POST", FNF_DELETE_ENDPOINT,
            json_body={"fnf": msisdn, "is_super": "1" if super_fnf else "0"},
            auth_mode=AuthMode.SUBSCRIBER,
        )
