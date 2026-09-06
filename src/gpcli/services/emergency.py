"""Emergency balance — GP's balance-loan system.

Wire contract (from `BalanceInterface` + `BalanceRepository.h()`, verified
against the decompiled sources and the live API):

* ``GET  /emergency-balance``  -> eligible amount + validity
* ``POST /emergency-balance``   -> body is an **empty JSON object**; response
  ``{"status": "..."}`` where ``"success"`` / ``"PENDING"`` mean accepted
* full state (due, total, opt-in flags, dynamic-EB limit) comes from
  ``GET /balance`` -> nested ``emergency_balance`` + ``settings`` (the app's
  eligibility rule: prepaid AND main balance < ``eb_eligibility_balance``,
  default 18 BDT, AND no active loan ``total == 0``)
"""

from __future__ import annotations

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import EmergencyBalance

EB_STATUS_ENDPOINT = "/emergency-balance"
EB_AVAIL_ENDPOINT = "/emergency-balance"
BALANCE_ENDPOINT = "/balance"
_OK_STATUSES = {"success", "pending"}


def _num(value: object, default: float) -> float:
    """Coerce wire numerics (float, int, or numeric string) to float."""
    if isinstance(value, bool):  # bool is an int subclass — not a balance
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


class EmergencyBalanceService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def status(self) -> EmergencyBalance:
        """`GET /emergency-balance` — the eligible amount and validity."""
        data = self.client.get_json("GET", EB_STATUS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return EmergencyBalance.model_validate(data)

    def full_state(self) -> dict:
        """`GET /balance` raw — main balance, nested EB block and EB settings."""
        return self.client.get_json("GET", BALANCE_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)

    def avail(self) -> dict:
        """`POST /emergency-balance` (empty body) — request the loan."""
        return self.client.get_json(
            "POST", EB_AVAIL_ENDPOINT, json_body={}, auth_mode=AuthMode.SUBSCRIBER
        )

    @staticmethod
    def is_avail_success(response: dict) -> bool:
        status = str(response.get("status", "")).lower() if isinstance(response, dict) else ""
        return status in _OK_STATUSES

    @staticmethod
    def eligibility(state: dict) -> dict:
        """App rules: prepaid, main balance under threshold, no active loan.

        The wire format is inconsistent — ``balance`` arrives as a number but
        ``settings.eb_eligibility_balance`` as a *string* — so both go through
        a tolerant numeric coercion before comparing.
        """
        main_balance = _num(state.get("balance"), 0.0)
        eb = state.get("emergency_balance") or {}
        settings = state.get("settings") or {}
        threshold = _num(settings.get("eb_eligibility_balance"), 18.0)
        active_loan = _num(eb.get("total"), 0.0) > 0
        return {
            "main_balance": main_balance,
            "threshold": threshold,
            "eligible": not active_loan and main_balance < threshold,
            "active_loan": active_loan,
        }
