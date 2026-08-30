"""Gamification — daily-login streak, milestone rewards, GP points.

Wire contract (from `LoginGamificationInterface`, `GamificationInterface`
and `Api.java` loyalty endpoints; recovered from the decompiled sources):

* ``GET  /v2/gamification/daily-login`` -> streak info (note: JSON key is
  ``milestone``, singular)
* ``POST /v2/gamification/daily-login/claim`` — body ``{"milestone_id": <id>}``;
  response ``{status: "success"|"pending", message, …}``
* ``GET  /loyalty/balance`` -> GP point balance + enrollment status
"""

from __future__ import annotations

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import ClaimResult, DailyLoginStreakInfo, RewardPointBalance

STREAK_ENDPOINT = "/v2/gamification/daily-login"
CLAIM_ENDPOINT = "/v2/gamification/daily-login/claim"
LOYALTY_BALANCE_ENDPOINT = "/loyalty/balance"


class GamificationService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def streak(self) -> DailyLoginStreakInfo:
        data = self.client.get_json("GET", STREAK_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return DailyLoginStreakInfo.model_validate(data)

    def claim(self, milestone_id: int) -> ClaimResult:
        data = self.client.get_json(
            "POST", CLAIM_ENDPOINT,
            json_body={"milestone_id": milestone_id},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return ClaimResult.model_validate(data)

    def points(self) -> RewardPointBalance:
        data = self.client.get_json("GET", LOYALTY_BALANCE_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        inner = data.get("data", data) if isinstance(data, dict) else {}
        return RewardPointBalance.model_validate(inner or {})
