"""Roaming — status, packs, usage history and web portals.

Findings from static analysis of the decompiled sources: MyGP 5.31.0 has
**no native roaming activation API**. The feature family is:

* status — ``GET /balance`` -> ``is_roaming`` (0/1); the app branches
  ``mygp://roaming`` on it (activation portal when off, offers when on)
* packs — ``GET /v3/catalogs`` with the ``roaming_offer`` attribute; the
  Taka/USD split is the ``roaming_mobile_balance`` / ``Buy_with_USD`` filters
* usage history — same ``GET /v2/usage_history`` feed; roaming items are those
  with ``usage_flag_type == "roaming"``; category menu comes from
  ``sub_menu.roaming``
* manage / rates / tips — WebView portals on roaming.grameenphone.com
  (activation/deactivation itself happens in the web portal; the app sends
  no API request for it)
"""

from __future__ import annotations

from datetime import date

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import PackItem, UsageHistoryResponse
from gpcli.services.catalog import CatalogService
from gpcli.services.history import HistoryService

# Web portals the app opens in a WebView for roaming management/rates/tips
# (decoded from the app's search config, assets/balance/balance.json).
ROAMING_MANAGE_URL = "https://roaming.grameenphone.com/roaming/digitalization/home"
ROAMING_RATES_URL = "https://roaming.grameenphone.com/personal/services/roaming/rate"
ROAMING_TIPS_URL = "https://roaming.grameenphone.com/personal/services/roaming"

ROAMING_FLAG = "roaming"  # usage_flag_type value marking roaming CDR items


class RoamingService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def status(self) -> dict:
        """`GET /balance` — the is_roaming flag drives the app's branching."""
        data = self.client.get_json("GET", "/balance", auth_mode=AuthMode.SUBSCRIBER)
        return {
            "is_roaming": bool(data.get("is_roaming", 0)),
            "balance": data.get("balance"),
            "type": data.get("type"),
        }

    def packs(self, *, usd: bool = False) -> list[PackItem]:
        """Roaming packs — Taka (mobile balance) or USD (Buy_with_USD)."""
        return CatalogService(self.client).category_packs("roaming", usd=usd)

    def usage(self, start: date, end: date) -> UsageHistoryResponse:
        """The CDR feed; roaming items are filtered client-side by the app."""
        return HistoryService(self.client).usage_history(start, end)

    @staticmethod
    def roaming_items(response: UsageHistoryResponse) -> list:
        """Items with `usage_flag_type == 'roaming'`, across all categories."""
        return [
            item
            for category in response.cdr
            for item in category.data
            if item.usage_flag_type == ROAMING_FLAG or "roaming" in (item.usage_flag or "")
        ]

    @staticmethod
    def roaming_menus(response: UsageHistoryResponse) -> dict:
        """The `sub_menu.roaming` category map (roaming-voice-history, …)."""
        sub_menu = response.sub_menu or {}
        roaming = sub_menu.get("roaming")
        return roaming if isinstance(roaming, dict) else {}
