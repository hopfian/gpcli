"""Offers & services — gifts, GA offers, pay-as-you-go, auto-renew, VAS set-status.

Wire formats (verified against the decompiled sources and the live API):

* Gifts: ``GET /v1/customers/gifts``; ``GET /gift-cards?offset&limit`` (limit=20)
* GA (gross add-on / new SIM): ``GET /ga-offer-details`` -> {ga_offer_details: {name: {…}}}
* PAYG: no dedicated endpoint — toggling "purchases" the catalog pack carrying the
  ``pay_go_on`` / ``pay_go_off`` attribute via ``POST /campaign-activate/`` with
  the app's `Api.l()` body. Status: ``GET /balance`` -> ``pay_go_status``.
* Auto-renew: ``GET /balance-status`` -> {internet: [], voice: []};
  ``POST /internet-renew {status: 0|1, productShortCode}`` (camelCase literal!)
* VAS set-status: ``POST services/v1/vas/set-status``
  single: {serviceId, chargeCode, partner, action: "active"|"deactive"}
  stop-all: {action: "deactive_all", partners: [], serviceIds: []}
"""

from __future__ import annotations

from gpcli.bodies import campaign_activate_body
from gpcli.client import ApiCaller, AuthMode
from gpcli.errors import MyGPError
from gpcli.models import BalanceStatusItem, GAOfferInfo, PackItem, ReceiverGift
from gpcli.services.catalog import CatalogService

__all__ = ["CAMPAIGN_ACTIVATE_ENDPOINT", "OffersService", "campaign_activate_body"]

GIFTS_ENDPOINT = "/v1/customers/gifts"
GIFT_CARDS_ENDPOINT = "/gift-cards"
GA_OFFERS_ENDPOINT = "/ga-offer-details"
CAMPAIGN_ACTIVATE_ENDPOINT = "/campaign-activate/"
BALANCE_STATUS_ENDPOINT = "/balance-status"
INTERNET_RENEW_ENDPOINT = "/internet-renew"
VAS_SET_STATUS_ENDPOINT = "/services/v1/vas/set-status"


class OffersService:
    def __init__(self, client: ApiCaller):
        self.client = client

    # ---------------------------------------------------------------- gifts

    def gifts(self) -> list[ReceiverGift]:
        data = self.client.get_json("GET", GIFTS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        items = data.get("data", []) if isinstance(data, dict) else []
        return [ReceiverGift.model_validate(item) for item in items if isinstance(item, dict)]

    def gift_cards(self, offset: int = 0, limit: int = 20) -> dict:
        return self.client.get_json(
            "GET", GIFT_CARDS_ENDPOINT,
            params={"offset": offset, "limit": limit},
            auth_mode=AuthMode.SUBSCRIBER,
        )

    # ------------------------------------------------------------- GA offers

    def ga_offer_details(self) -> dict[str, GAOfferInfo]:
        data = self.client.get_json("GET", GA_OFFERS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        details = data.get("ga_offer_details", {}) if isinstance(data, dict) else {}
        return {
            name: GAOfferInfo.model_validate(info)
            for name, info in details.items()
            if isinstance(info, dict)
        }

    # ------------------------------------------------------------------ PAYG

    def payg_status(self) -> str:
        data = self.client.get_json("GET", "/balance", auth_mode=AuthMode.SUBSCRIBER)
        return str(data.get("pay_go_status", "") or "")

    def payg_packs(self) -> tuple[PackItem | None, PackItem | None]:
        """(on_pack, off_pack) — feature is only usable when both exist."""
        packs = CatalogService(self.client).packs()
        on = next((p for p in packs if "pay_go_on" in p.attributes), None)
        off = next((p for p in packs if "pay_go_off" in p.attributes), None)
        return on, off

    def payg_toggle(self, enable: bool) -> dict:
        """`POST /campaign-activate/` with the pay_go_on/pay_go_off pack."""
        on_pack, off_pack = self.payg_packs()
        pack = on_pack if enable else off_pack
        if pack is None:
            direction = "pay_go_on" if enable else "pay_go_off"
            raise MyGPError(f"no {direction} pack in the catalog — PAYG toggle unavailable")
        msisdn = self.client.state.auth.msisdn if self.client.state.auth else "0"
        return self.client.get_json(
            "POST", CAMPAIGN_ACTIVATE_ENDPOINT,
            json_body=campaign_activate_body(pack, msisdn),
            auth_mode=AuthMode.SUBSCRIBER,
        )

    # ------------------------------------------------------------ auto-renew

    def balance_status(self) -> dict[str, list[BalanceStatusItem]]:
        data = self.client.get_json("GET", BALANCE_STATUS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        result: dict[str, list[BalanceStatusItem]] = {}
        for kind in ("internet", "voice"):
            items = data.get(kind, []) if isinstance(data, dict) else []
            result[kind] = [
                BalanceStatusItem.model_validate(i) for i in items if isinstance(i, dict)
            ]
        return result

    def set_auto_renew(self, product_short_code: str, enabled: bool) -> dict:
        """`POST /internet-renew {status, productShortCode}` — camelCase literal."""
        return self.client.get_json(
            "POST", INTERNET_RENEW_ENDPOINT,
            json_body={"status": 1 if enabled else 0, "productShortCode": product_short_code},
            auth_mode=AuthMode.SUBSCRIBER,
        )

    # -------------------------------------------------------------- VAS mgmt

    def vas_activate(self, service: dict) -> dict:
        return self.client.get_json(
            "POST", VAS_SET_STATUS_ENDPOINT,
            json_body={
                "serviceId": service.get("service_id", ""),
                "chargeCode": service.get("charge_code", ""),
                "partner": service.get("partner", ""),
                "action": "active",
            },
            auth_mode=AuthMode.SUBSCRIBER,
        )

    def vas_deactivate(self, service: dict) -> dict:
        return self.client.get_json(
            "POST", VAS_SET_STATUS_ENDPOINT,
            json_body={
                "serviceId": service.get("service_id") or service.get("type", ""),
                "chargeCode": service.get("charge_code", ""),
                "partner": service.get("partner", ""),
                "action": "deactive",
            },
            auth_mode=AuthMode.SUBSCRIBER,
        )

    def vas_stop_all(self, services: list[dict]) -> dict:
        partners = sorted({s.get("partner", "") for s in services} - {""})
        service_ids = sorted({(s.get("service_id") or s.get("type", "")) for s in services} - {""})
        return self.client.get_json(
            "POST", VAS_SET_STATUS_ENDPOINT,
            json_body={
                "action": "deactive_all",
                "partners": partners,
                "serviceIds": service_ids,
            },
            auth_mode=AuthMode.SUBSCRIBER,
        )
