"""Usage history, bill cycles and autopay services."""

from datetime import date, timedelta

import pytest
from constants import MSISDN_880, MSISDN_LOCAL

from gpcli.errors import MyGPError
from gpcli.models import UsageHistoryItem, UsageHistoryResponse
from gpcli.services.autopay import AutoPayService, local_msisdn
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


_PRODUCTS = [
    {"product_type": "low_balance", "product_code": "AP_LOW",
     "frequency_unit": "day", "trigger_amount": "18"},
    {"product_type": "scheduled_recharge", "product_code": "AP_SCHED",
     "frequency_unit": "day", "frequency": ["1", "7", "30"]},
]


def _subscription_list(rec) -> None:
    rec.add("GET", "/v1/auto-payment/subscription-list", json={
        "data": {"setting": {"products": _PRODUCTS}, "subscription": []},
    })


class TestAutoPaySubscriptionBodies:
    """`setup`/`update`/`cancel` wire contracts (money-adjacent)."""

    def test_setup_low_balance_defaults(self, make_client, state):
        import json as _json

        client, rec = make_client()
        _subscription_list(rec)
        rec.add("POST", "/v1/auto-payment/pay", json={"status": "success"})
        AutoPayService(client).setup(
            amount="50", provisioning_msisdn=MSISDN_880,
            service_provider="nagad", service_provider_identifier="tok",
        )
        body = _json.loads(rec.requests[-1].content)
        assert body["product_type"] == "low_balance"
        assert body["product_code"] == "AP_LOW"
        assert body["frequency"] == ""  # low-balance mode: no frequency
        assert body["provisioning_msisdn"] == MSISDN_LOCAL
        assert body["service_provider"] == "nagad"
        assert body["conn_type"] == "prepaid"
        assert body["start_from"] == (date.today() + timedelta(days=1)).isoformat()

    def test_setup_scheduled_uses_the_scheduled_product(self, make_client, state):
        import json as _json

        client, rec = make_client()
        _subscription_list(rec)
        rec.add("POST", "/v1/auto-payment/pay", json={"status": "success"})
        AutoPayService(client).setup(
            amount="50", provisioning_msisdn=MSISDN_880,
            service_provider="nagad", service_provider_identifier="tok",
            frequency="7", start_from=date(2026, 10, 1),
        )
        body = _json.loads(rec.requests[-1].content)
        assert body["product_type"] == "scheduled_recharge"
        assert body["product_code"] == "AP_SCHED"
        assert body["frequency"] == "7"
        assert body["start_from"] == "2026-10-01"

    def test_setup_without_a_configured_product_raises(self, make_client, state):
        client, rec = make_client()
        rec.add("GET", "/v1/auto-payment/subscription-list", json={
            "data": {"setting": {"products": []}, "subscription": []},
        })
        with pytest.raises(MyGPError, match="products"):
            AutoPayService(client).setup(
                amount="50", provisioning_msisdn=MSISDN_880,
                service_provider="bkash", service_provider_identifier="tok",
            )

    def test_update_uses_the_put_endpoint(self, make_client, state):
        import json as _json

        client, rec = make_client()
        _subscription_list(rec)
        rec.add("PUT", "/v1/auto-payment/55/update", json={"status": "success"})
        AutoPayService(client).update(
            55, amount="100", provisioning_msisdn=MSISDN_880,
            service_provider="bkash", service_provider_identifier="tok",
            frequency="30",
        )
        body = _json.loads(rec.requests[-1].content)
        assert body["amount"] == "100"
        assert body["frequency"] == "30"
        assert body["product_type"] == "scheduled_recharge"
        assert "55/update" in str(rec.requests[-1].url)

    def test_cancel_uses_delete_with_query_param(self, make_client, state):
        client, rec = make_client()
        rec.add("DELETE", "/v1/auto-payment/55/cancel", json={"status": "success"})
        AutoPayService(client).cancel(55, MSISDN_880)
        request = rec.requests[-1]
        assert "55/cancel" in str(request.url)
        assert request.url.params["provisioning_msisdn"] == MSISDN_LOCAL
