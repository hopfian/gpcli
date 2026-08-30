"""Usage history — the prepaid CDR feed (`GET /v2/usage_history`).

Wire contract (from `UsageHistoryApiService` + `UsageHistoryDataImpl`):
* dates on the wire are ``yyyy-MM-dd`` (converted internally by the app from
  ``dd-MM-yyyy`` UI format)
* the app's default window is the first ``_meta.filters`` entry
  (``filter_day``, typically 7): start = today − (N−1), end = today
* item-level ``usage_date`` is ``dd-MM-yyyy``
"""

from __future__ import annotations

from datetime import date, timedelta

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import UsageHistoryResponse

USAGE_HISTORY_ENDPOINT = "/v2/usage_history"


def default_window(days: int = 7, *, today: date | None = None) -> tuple[date, date]:
    """App logic: inclusive window ending today."""
    today = today or date.today()
    return today - timedelta(days=days - 1), today


class HistoryService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def usage_history(self, start: date, end: date) -> UsageHistoryResponse:
        data = self.client.get_json(
            "GET", USAGE_HISTORY_ENDPOINT,
            params={"cdr_start_date": start.isoformat(), "cdr_end_date": end.isoformat()},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return UsageHistoryResponse.model_validate(data)
