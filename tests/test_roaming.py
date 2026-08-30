"""Roaming service — status, item filtering, portal URLs."""

from gpcli.models import UsageHistoryItem, UsageHistoryResponse
from gpcli.services.roaming import (
    ROAMING_MANAGE_URL,
    ROAMING_RATES_URL,
    ROAMING_TIPS_URL,
    RoamingService,
)


def _response_with(*items: dict) -> UsageHistoryResponse:
    return UsageHistoryResponse.model_validate({
        "cdr": [{"title": "Roaming", "type": "roaming", "slug": "roaming-history", "data": list(items)}],
        "sub_menu": {"roaming": {"roaming-voice-history": {"title": "Roaming Call History", "visible": 1}}},
    })


class TestRoamingStatus:
    def test_is_roaming_flag(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"is_roaming": 1, "balance": 5.25, "type": "prepaid"})
        info = RoamingService(client).status()
        assert info["is_roaming"] is True
        assert info["balance"] == 5.25

    def test_off_by_default(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"balance": 0})
        assert RoamingService(client).status()["is_roaming"] is False


class TestRoamingItemFilter:
    def test_filters_by_usage_flag_type(self):
        response = _response_with(
            {"b_party": "x", "usage_flag_type": "roaming", "usage_charge": "10"},
            {"b_party": "y", "usage_flag_type": "ebadjust"},
            {"b_party": "z", "usage_flag": "roaming day 1"},  # legacy flag match
        )
        items = RoamingService.roaming_items(response)
        assert len(items) == 2
        assert {i.b_party for i in items} == {"x", "z"}

    def test_no_items(self):
        assert RoamingService.roaming_items(_response_with()) == []

    def test_menus_extracted(self):
        response = _response_with()
        menus = RoamingService.roaming_menus(response)
        assert "roaming-voice-history" in menus
        assert menus["roaming-voice-history"]["title"] == "Roaming Call History"

    def test_menus_empty_safely(self):
        response = UsageHistoryResponse.model_validate({"cdr": []})
        assert RoamingService.roaming_menus(response) == {}


class TestPortalUrls:
    def test_urls_decoded_from_app_config(self):
        assert ROAMING_MANAGE_URL.startswith("https://roaming.grameenphone.com/roaming/digitalization")
        assert ROAMING_RATES_URL.endswith("/roaming/rate")
        assert ROAMING_TIPS_URL.endswith("/roaming")


def test_usage_flag_type_field_parses():
    item = UsageHistoryItem.model_validate({"usage_flag_type": "roaming"})
    assert item.usage_flag_type == "roaming"
