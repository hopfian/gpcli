"""Usage history, bill cycles and autopay services."""

from datetime import date

from constants import MSISDN_880, MSISDN_LOCAL

from gpcli.models import UsageHistoryItem, UsageHistoryResponse
from gpcli.services.autopay import local_msisdn
from gpcli.services.billing import _add_months, bill_cycles
from gpcli.services.history import default_window


class TestDefaultWindow:
    def test_seven_days_inclusive(self):
        start, end = default_window(7, today=date(2026, 8, 30))
        assert start == date(2026, 8, 24)
        assert end == date(2026, 8, 30)

    def test_one_day(self):
        start, end = default_window(1, today=date(2026, 8, 30))
        assert start == end == date(2026, 8, 30)

    def test_month_boundary(self):
        start, _ = default_window(7, today=date(2026, 9, 2))
        assert start == date(2026, 8, 27)


class TestAddMonths:
    def test_clamps_day(self):
        assert _add_months(date(2026, 3, 31), -1) == date(2026, 2, 28)
        assert _add_months(date(2024, 3, 31), -1) == date(2024, 2, 29)  # leap year

    def test_year_rollover(self):
        assert _add_months(date(2026, 1, 15), -2) == date(2025, 11, 15)


class TestBillCycles:
    def test_six_cycles_anchored(self):
        cycles = bill_cycles(date(2026, 2, 5))
        assert len(cycles) == 6
        first = cycles[0]
        assert first.invoice_month == "2026-02-05"
        assert first.start == "2026-01-05"
        assert first.end == "2026-02-04"
        assert cycles[1].invoice_month == "2026-01-05"  # 5th of Jan (clamped)
        assert cycles[5].invoice_month == "2025-09-05"

    def test_day_clamp(self):
        cycles = bill_cycles(date(2026, 3, 31))
        assert cycles[1].invoice_month == "2026-02-28"
        assert cycles[1].start == "2026-01-28"  # Feb 28 − 1 month (Calendar clamping)


class TestUsageHistoryModels:
    def test_item_helpers(self):
        item = UsageHistoryItem(usage_type="0", usage_charge="12.5", b_party="017")
        assert item.direction == "out"
        assert item.charge == "12.50"
        incoming = UsageHistoryItem(usage_type="1", usage_charge="")
        assert incoming.direction == "in"
        assert incoming.charge == "0.00"

    def test_response_aliases(self):
        response = UsageHistoryResponse.model_validate({"_meta": {"filters": [{"slug": "7_days"}]}})
        assert response.meta["filters"][0]["slug"] == "7_days"


class TestLocalMsisdn:
    def test_formats(self):
        assert local_msisdn(MSISDN_880) == MSISDN_LOCAL
        assert local_msisdn(MSISDN_LOCAL) == MSISDN_LOCAL
        assert local_msisdn("+880 1700-000 000") == MSISDN_LOCAL
