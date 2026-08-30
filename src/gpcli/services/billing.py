"""Itemized bill — postpaid PDF statements.

Wire contract (from `Api.h`, `ItemizedBillActivity`, `ItemizedBillViewModel`):
* ``POST /itemized-bill`` body ``{"invoice_month": "yyyy-MM-dd", "invoice_type": "local"|"roaming"}``
* response body is the raw PDF binary (the app streams it to a file with no
  validation — this client checks the ``%PDF`` magic)
* ``invoice_month`` = the bill-generation anchor date (from
  ``current-usage.last_billed_on``, fallback today), for the last 6 cycles
* each cycle covers ``[invoice_month − 1 month, invoice_month − 1 day]``
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from pathlib import Path

from gpcli.client import ApiCaller, AuthMode
from gpcli.constants import USAGE_ENDPOINT
from gpcli.errors import ApiError, MyGPError
from gpcli.models import BillCycle

ITEMIZED_BILL_ENDPOINT = "/itemized-bill"
BILL_CYCLE_COUNT = 6


def _add_months(anchor: date, months: int) -> date:
    """Java Calendar.add(MONTH, n) semantics with day-of-month clamping."""
    month_index = anchor.month - 1 + months
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def bill_cycles(anchor: date, count: int = BILL_CYCLE_COUNT) -> list[BillCycle]:
    """The app's 6 selectable cycles: anchor, anchor−1mo, …, anchor−5mo."""
    cycles = []
    for k in range(count):
        month = _add_months(anchor, -k)
        start = _add_months(month, -1)
        end = month - timedelta(days=1)
        cycles.append(BillCycle(
            invoice_month=month.isoformat(),
            start=start.isoformat(),
            end=end.isoformat(),
        ))
    return cycles


class BillService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def anchor(self) -> date:
        """Bill-generation anchor: current-usage.last_billed_on, fallback today."""
        try:
            data = self.client.get_json("GET", USAGE_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        except MyGPError:
            return date.today()
        # current-usage shape: {"last_billed_on": "yyyy-MM-dd", ...} (or error envelope)
        raw = data.get("last_billed_on") if isinstance(data, dict) else None
        if not raw:
            return date.today()
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return date.today()

    def cycles(self, anchor: date | None = None) -> list[BillCycle]:
        return bill_cycles(anchor or self.anchor())

    def itemized_pdf(self, invoice_month: str, invoice_type: str, out_path: Path) -> Path:
        """Download an itemized bill PDF. Validates the %PDF magic (the app doesn't)."""
        if invoice_type not in ("local", "roaming"):
            raise ValueError("invoice_type must be 'local' or 'roaming'")
        response = self.client.request(
            "POST", ITEMIZED_BILL_ENDPOINT,
            json_body={"invoice_month": invoice_month, "invoice_type": invoice_type},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        if response.status_code != 200:
            raise ApiError(
                response.status_code,
                f"itemized-bill request failed: {response.text[:150]}",
            )
        content = response.content
        if not content.startswith(b"%PDF"):
            raise ApiError(None, "response is not a PDF (postpaid-only feature?)",
                           content[:120].decode("utf-8", "replace"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(content)
        return out_path
