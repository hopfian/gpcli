"""Subscriber account endpoints (legacy gateway)."""

from __future__ import annotations

from gpcli.client import ApiCaller, AuthMode
from gpcli.constants import (
    BALANCE_ENDPOINT,
    CUSTOMER_STATUS_ENDPOINT,
    ME_ENDPOINT,
    USAGE_ENDPOINT,
)
from gpcli.models import Balance, Me


class AccountService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def me(self) -> Me:
        """`GET /me` — subscriber identity and profile."""
        data = self.client.get_json("GET", ME_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return Me.model_validate(data)

    def balance(self) -> Balance:
        """`GET /balance` — main balance, packages, emergency balance."""
        data = self.client.get_json("GET", BALANCE_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return Balance.model_validate(data)

    def usage(self) -> dict:
        """`GET /current-usage` — usage snapshot (raw; the app caches this)."""
        return self.client.get_json("GET", USAGE_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)

    def customer_status(self) -> dict:
        """`GET /v1/customers/status` — SIM/foreigner flags."""
        return self.client.get_json("GET", CUSTOMER_STATUS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
