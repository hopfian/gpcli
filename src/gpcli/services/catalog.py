"""Catalog services — flexiplan price matrix and VAS (value-added services).

Wire formats verified live 2026-08-30. The bundle key/value encoding is
replicated from `FlexiplanHelperKt` (see decompiled sources):

* key:   ``L{days}_V{voice}_D{dataMB}M_F{4gMB}M_B{bioscopeMB}M_S{sms}``
  (app keywords prefix these with ``FLXPLN_V2_`` and express data in GB)
* value: ``B{base}_M{market}_C{commission}_T{baseVat}_P{prepaidPriceVatMCA}_S{postpaid}_D{discount}``
"""

from __future__ import annotations

import re
from typing import Any

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import (
    FlexiBundlePrice,
    FlexiPlan,
    PackItem,
    VasCategory,
    VasService,
)

FLEXIPLAN_CATALOG_ENDPOINT = "/catalogs/v2/flexiplans"
VAS_CATEGORIES_ENDPOINT = "/catalogs/services/v1/vas/get-categories"
VAS_SERVICES_ENDPOINT = "/catalogs/services/v1/vas/get-services"
VAS_SUBSCRIPTIONS_ENDPOINT = "/services/v1/vas/get-subscription-details"
VAS_HISTORY_ENDPOINT = "/services/v1/vas/get-history"
PACK_CATALOG_ENDPOINT = "/v3/catalogs"
CMP_OFFERS_ENDPOINT = "/v2/cmp-offers"

# filters that mark a pack as an entertainment/streaming partner pack
# (observed live: hoichoi, chorki, bioscope, sonyliv, lionsgate, ...)
_ENTERTAINMENT_FILTERS = {
    "hoichoi", "chorki", "streaming", "bioscope", "bioscope-web", "sonyliv",
    "lionsgate", "i-screen", "deeptoplay", "tsports", "shemaroome",
    "rabbithole", "epicon", "docubay", "klikk", "shukhee", "utshob",
}
_ROAMING_USD_FILTER = "Buy_with_USD"
_ROAMING_BDT_FILTER = "roaming_mobile_balance"

# category slugs the app's Explore tabs use (Tab.kt), mapped to pack predicates
PACK_CATEGORIES: dict[str, str] = {
    "internet": "type == internet",
    "bundles": "type == bundle",
    "minutes": "type == voice",
    "sms": "type == sms",
    "cashback": "type == recharge_offer",
    "gifts": "attribute giftable_offer / gift_only_offer",
    "rate-cutter": "attribute rate_cutter_offer / free_rate_cutter_offer",
    "roaming": "attribute roaming_offer",
    "entertainment": "attribute entertainment_offer or streaming filters",
    "subscriptions": "type == subscription or attribute subscription_item",
    "health": "tab membership: tabs_priority['health'] (Shukhee bundles)",
    "my-offers": "personalized CMP offers (v2/cmp-offers)",
    "all": "the entire pack catalog",
}


def _in_category(category: str, pack: PackItem, *, usd: bool = False) -> bool:
    attrs = set(pack.attributes)
    filters = set(pack.filters)
    if category == "internet":
        return pack.type == "internet"
    if category == "bundles":
        return pack.type == "bundle"
    if category == "minutes":
        return pack.type == "voice"
    if category == "sms":
        return pack.type == "sms"
    if category == "cashback":
        return pack.type == "recharge_offer"
    if category == "gifts":
        return bool(attrs & {"giftable_offer", "gift_only_offer", "recharge_giftable_offer"})
    if category == "rate-cutter":
        return bool(attrs & {"rate_cutter_offer", "free_rate_cutter_offer"})
    if category == "roaming":
        if "roaming_offer" not in attrs:
            return False
        if usd:
            return _ROAMING_USD_FILTER in filters
        return _ROAMING_BDT_FILTER in filters or _ROAMING_USD_FILTER not in filters
    if category == "entertainment":
        return "entertainment_offer" in attrs or bool(filters & _ENTERTAINMENT_FILTERS)
    if category == "subscriptions":
        return pack.type == "subscription" or "subscription_item" in attrs
    return True  # all


_KEY_SEGMENT_RE = re.compile(r"^([A-Z])(-?\d+(?:\.\d+)?)")


def _vol(mb: int) -> str:
    """Volume segment encoding observed on the wire: `0M`, `{gb}G` or `{mb}M`."""
    if mb == 0:
        return "0M"
    if mb % 1024 == 0:
        return f"{mb // 1024}G"
    return f"{mb}M"


def build_bundle_key(
    days: int,
    voice: int = 0,
    data_mb: int = 0,
    data4g_mb: int = 0,
    bioscope_mb: int = 0,
    sms: int = 0,
) -> str:
    """Build the catalog bundle key for a combination."""
    return (
        f"L{days}_V{voice}_D{_vol(data_mb)}_F{_vol(data4g_mb)}_B{_vol(bioscope_mb)}_S{sms}"
    )


def parse_bundle_price(value: str) -> FlexiBundlePrice:
    """Decode a `bundles` value (`B.._M.._C.._T.._P.._S.._D..`)."""
    fields: dict[str, float] = {}
    for segment in value.split("_"):
        match = _KEY_SEGMENT_RE.match(segment)
        if not match:
            continue
        letter, number = match.groups()
        fields[letter] = float(number)
    discount = fields.get("D", 0.0)
    return FlexiBundlePrice(
        base_price=fields.get("B", 0.0),
        market_price=fields.get("M", 0.0),
        commission=fields.get("C", 0.0),
        base_price_vat=fields.get("T", 0.0),
        price_vat_mca_prepaid=fields.get("P", 0.0),
        price_vat_mca_postpaid=fields.get("S", 0.0),
        discount_percent=int(discount + 0.999999) if discount else 0,  # app: ceil
    )


def quote_flexiplan(
    catalog: FlexiPlan,
    days: int,
    voice: int = 0,
    data_mb: int = 0,
    data4g_mb: int = 0,
    bioscope_mb: int = 0,
    sms: int = 0,
) -> tuple[str, FlexiBundlePrice]:
    """Look up the price for a bundle combination. Raises KeyError if absent."""
    key = build_bundle_key(days, voice, data_mb, data4g_mb, bioscope_mb, sms)
    try:
        raw = catalog.bundles[key]
    except KeyError as err:
        raise KeyError(f"no bundle priced for {key}") from err
    return key, parse_bundle_price(raw)


class CatalogService:
    def __init__(self, client: ApiCaller):
        self.client = client
        self.tabs_priority: dict[str, list] = {}

    # --------------------------------------------------------- pack catalog

    def packs(self) -> list[PackItem]:
        """`GET v3/catalogs` — the app's master pack catalog (351+ packs)."""
        data = self.client.get_json(
            "GET", PACK_CATALOG_ENDPOINT,
            params={"bs_user": 0, "with_personalized_bonus": 1, "hash": ""},
            headers={"Cache-Control": "no-cache"},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        self.tabs_priority = (
            data.get("tabs_priority", {}) if isinstance(data, dict) else {}
        )
        items = data.get("catalogs", []) if isinstance(data, dict) else []
        return [PackItem.model_validate(item) for item in items if isinstance(item, dict)]

    def category_packs(self, category: str, *, usd: bool = False) -> list[PackItem]:
        packs = self.packs()
        if category == "health":
            # dynamic tab: pack IDs listed under tabs_priority["health"]
            health_ids = set(self.tabs_priority.get("health", []) or [])
            packs = [p for p in packs if p.id in health_ids]
        else:
            packs = [p for p in packs if _in_category(category, p, usd=usd)]
        return _sort_packs(packs)

    def cmp_offers(self) -> dict[str, Any]:
        """`GET v2/cmp-offers` — personalized campaign offers (my offers)."""
        return self.client.get_json(
            "GET", CMP_OFFERS_ENDPOINT,
            headers={"Cache-Control": "no-cache"},
            auth_mode=AuthMode.SUBSCRIBER,
        )

    # ------------------------------------------------------------ flexiplan

    def flexiplans(self) -> FlexiPlan:
        """`GET catalogs/v2/flexiplans?hash=` — hash acts as an ETag (empty on first call)."""
        data = self.client.get_json(
            "GET", FLEXIPLAN_CATALOG_ENDPOINT,
            params={"hash": ""},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return FlexiPlan.model_validate(data)

    # ------------------------------------------------------------------ VAS

    def vas_categories(self) -> list[VasCategory]:
        data = self.client.get_json("GET", VAS_CATEGORIES_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return [VasCategory.model_validate(item) for item in data.get("data", [])]

    def vas_services(self, category_id: int) -> list[VasService]:
        data = self.client.get_json(
            "GET", VAS_SERVICES_ENDPOINT,
            params={"categoryId": category_id},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return [VasService.model_validate(item) for item in data.get("data", [])]

    def vas_subscriptions(self) -> list[dict[str, Any]]:
        """Active VAS subscriptions (raw items — shape varies by type)."""
        data = self.client.get_json("GET", VAS_SUBSCRIPTIONS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return data.get("data", []) if isinstance(data, dict) else []

    def vas_history(self) -> list[dict[str, Any]]:
        data = self.client.get_json("GET", VAS_HISTORY_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return data.get("data", []) if isinstance(data, dict) else []


def _sort_packs(packs: list[PackItem]) -> list[PackItem]:
    """Price ascending (non-numeric prices last)."""
    return sorted(packs, key=lambda p: (p.price_value is None, p.price_value or 0.0))
