"""Purchase & recharge — the full money-movement flows.

Wire formats (verified against the decompiled sources and the live API —
from RechargeApiInterface / RechargeAndActivateUseCaseImpl smali /
PurchaseHelper / RechargeHelper):

* ``POST /recharge`` — gateway selection; body = the `Recharge` object (raw
  field names, ``platform="android"``, ``metadata`` alias); response carries
  per-MFS payment URLs (``payment_url`` / ``bkash_url`` / ``rocket_url``)
  that the app loads in a payment WebView.
* ``POST /payment-gateway/payment`` — wallet/one-tap direct payment; body =
  `MakePaymentBody` ({amount, recharge_msisdn, service_provider, identifier,
  eb_due, channel, main_balance, ...}); success only when ``status == "success"``.
* ``POST /recharge-and-activate`` — modern pack purchase; body::

      {recharge_data: <MakePaymentBody serialized>,
       pack_data:    <Api.l(pack) body + forced="1" + otp?>,
       recharge_type: "direct_recharge",
       pack_type: "campaign"|"cmp"|"flexiplan",
       journey_type: "recharge_and_activate"|"trigger",
       is_recharge_giftable: "0"|"1"}

  response ``data.status``: "action_required" -> data.url.payment_url (WebView);
  "success"/"pending" -> direct_recharge info.
* ``POST /campaign-activate/`` — legacy pack activation (free/zero-price packs,
  PAYG); body = Api.l(pack, msisdn) (see offers.campaign_activate_body).
* ``GET  /recharge/offer`` — top-level array [{condition, text, type}]
* ``GET  orders/v1/bill-payments`` — {result: [...], settings}
"""

from __future__ import annotations

import math
from typing import Any

from gpcli.bodies import (
    build_pack_data,  # noqa: F401 — re-exported for command layer
    build_recharge_data,
    campaign_activate_body,
    pack_recharge_journey,
)
from gpcli.client import ApiCaller, AuthMode
from gpcli.models import (
    MakePaymentResult,
    PackItem,
    PaymentHistory,
    RechargeAndActivateResponse,
    RechargeGatewayResult,
    RechargeOffer,
)
from gpcli.msisdn import local_msisdn, normalize_msisdn
from gpcli.services.catalog import CatalogService
from gpcli.services.offers import CAMPAIGN_ACTIVATE_ENDPOINT

RECHARGE_ENDPOINT = "/recharge"
PAYMENT_GATEWAY_ENDPOINT = "/payment-gateway/payment"
RECHARGE_AND_ACTIVATE_ENDPOINT = "/recharge-and-activate"
RECHARGE_OFFER_ENDPOINT = "/recharge/offer"
PAYMENT_HISTORY_ENDPOINT = "/orders/v1/bill-payments"


def _eb_due_from(balance: dict[str, Any]) -> float:
    """`getTotalEmergencyBalance()` = ceil(max(due,0) + max(data_loan,0))."""
    eb = balance.get("emergency_balance", {}) if isinstance(balance, dict) else {}
    due = max(float(eb.get("due") or 0), 0.0)
    loan = max(float(eb.get("data_loan") or 0), 0.0)
    return math.ceil(due + loan)


def _balance_snapshot(client: ApiCaller) -> dict[str, Any]:
    try:
        data = client.get_json("GET", "/balance", auth_mode=AuthMode.SUBSCRIBER)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class PurchaseService:
    def __init__(self, client: ApiCaller):
        self.client = client

    # ------------------------------------------------------------ discovery

    def find_pack(self, ref: str) -> PackItem | None:
        """Locate a catalog pack by numeric id or keyword substring."""
        for pack in CatalogService(self.client).packs():
            if pack.id == ref or (ref and ref.lower() in pack.keyword.lower()):
                return pack
        return None

    def recharge_offers(self) -> list[RechargeOffer]:
        data = self.client.get_json(
            "GET", RECHARGE_OFFER_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER
        )
        items = data if isinstance(data, list) else []
        return [RechargeOffer.model_validate(i) for i in items if isinstance(i, dict)]

    def payment_history(self) -> PaymentHistory:
        data = self.client.get_json(
            "GET", PAYMENT_HISTORY_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER
        )
        return PaymentHistory.model_validate(data if isinstance(data, dict) else {})

    # ------------------------------------------------------------- gateway

    def recharge_gateway(
        self,
        amount: int,
        *,
        msisdn: str = "",
        channel: str = "",
        pack: PackItem | None = None,
    ) -> RechargeGatewayResult:
        """`POST /recharge` — the `Recharge` object; returns MFS payment URLs."""
        state = self.client.state
        auth = state.auth
        msisdn_880 = normalize_msisdn(msisdn or (auth.msisdn if auth else "8801"))
        email = f"{msisdn_880}@grameenphone.com"
        balance = _balance_snapshot(self.client)
        body: dict[str, Any] = {
            "name": msisdn_880,
            "mobile": local_msisdn(msisdn_880),
            "email": email,
            "platform": "android",
            "amount": amount,
            "channel": channel or self._pack_channel(pack),
            "type": "PREPAID",
            "main_balance": str(balance.get("balance", 0) or 0),
            "connection_type": "prepaid",
            "eb_due": _eb_due_from(balance),
            "date": "",
            "zero_rated": 0,
            "is_new_user": 0,
            "is_cmp": 0,
            "is_personalized": 0,
            "isCashbackOffer": False,
            "changePaymentMethod": False,
            "back_to_home": False,
            "rechargeSource": "DEFAULT",
        }
        if pack is not None:
            body.update({
                "campaign": pack.additional_data.get("recharge_campaign_id") or "",
                "pack_name": pack.title,
                "crm_keyword": pack.keyword,
                "catalog_id": pack.id,
                "card_id": pack.additional_data.get("card_id") or "",
            })
        data = self.client.get_json(
            "POST", RECHARGE_ENDPOINT, json_body=body, auth_mode=AuthMode.SUBSCRIBER
        )
        return RechargeGatewayResult.model_validate(data if isinstance(data, dict) else {})

    def _main_balance(self) -> str:
        return str(_balance_snapshot(self.client).get("balance", 0) or 0)

    @staticmethod
    def _pack_channel(pack: PackItem | None) -> str:
        """RechargeHelper.c() channel derivation."""
        if pack is None:
            return ""
        journey = pack_recharge_journey(pack)
        sub = journey.get("sub_channel") or journey.get("subChannel") or ""
        if sub:
            return str(sub)
        if "recharge_journey_offer" in pack.attributes or "prime_trigger_offer" in pack.attributes:
            return "direct_recharge_offer"
        if "flexiplan_offer" in pack.attributes or (pack.keyword or "").upper().startswith("FLXPLN"):
            return "recharge_and_activate_flexiplan"
        return "recharge_and_activate_eb"

    # -------------------------------------------------------- wallet payment

    def pay(
        self,
        amount: str,
        *,
        provider: str,
        identifier: str,
        msisdn: str = "",
        channel: str = "",
    ) -> MakePaymentResult:
        """`POST /payment-gateway/payment` — MakePaymentBody."""
        state = self.client.state
        auth = state.auth
        msisdn_880 = normalize_msisdn(msisdn or (auth.msisdn if auth else "8801"))
        balance = _balance_snapshot(self.client)
        body = {
            "amount": str(amount),
            "recharge_msisdn": local_msisdn(msisdn_880),
            "service_provider": provider,
            "eb_due": _eb_due_from(balance),
            "campaign_code": None,
            "channel": channel or "direct_recharge_offer",
            "pack_name": None,
            "crm_keyword": None,
            "main_balance": str(balance.get("balance", 0) or 0),
            "identifier": identifier,
            "channel_code": None,
            "is_personalized": 0,
            "is_new_user": 0,
            "catalog_id": None,
            "card_id": None,
            "connection_type": "prepaid",
            "b_party_connection_type": None,
        }
        data = self.client.get_json(
            "POST", PAYMENT_GATEWAY_ENDPOINT, json_body=body, auth_mode=AuthMode.SUBSCRIBER
        )
        return MakePaymentResult.model_validate(data if isinstance(data, dict) else {})

    # --------------------------------------------------------- pack purchase

    def purchase_pack(
        self,
        pack: PackItem,
        *,
        msisdn: str = "",
        otp: str = "",
        recharge_amount: int | None = None,
        provider: str = "",
        identifier: str = "",
    ) -> RechargeAndActivateResponse:
        """`POST /recharge-and-activate` — the modern pack-purchase flow."""
        state = self.client.state
        auth = state.auth
        msisdn_880 = normalize_msisdn(msisdn or (auth.msisdn if auth else "8801"))
        amount = recharge_amount if recharge_amount is not None else int(pack.price_value or 0)
        balance = _balance_snapshot(self.client)

        recharge_data = build_recharge_data(
            amount=amount,
            msisdn=msisdn_880,
            provider=provider,
            identifier=identifier,
            main_balance=str(balance.get("balance", 0) or 0),
            eb_due=_eb_due_from(balance),
            pack=pack,
        )
        pack_data = build_pack_data(pack, msisdn_880, otp=otp, recharge=amount)
        body = {
            "recharge_data": recharge_data,
            "pack_data": pack_data,
            "recharge_type": "direct_recharge",
            "pack_type": "campaign",
            "journey_type": "recharge_and_activate",
            "is_recharge_giftable": "1" if "recharge_giftable_offer" in pack.attributes else "0",
        }
        data = self.client.get_json(
            "POST", RECHARGE_AND_ACTIVATE_ENDPOINT,
            json_body=body,
            headers=self._purchase_headers(balance),
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return RechargeAndActivateResponse.model_validate(data if isinstance(data, dict) else {})

    def purchase_legacy(self, pack: PackItem, *, msisdn: str = "") -> dict:
        """`POST /campaign-activate/` — the legacy activation (free/PAYG packs)."""
        auth = self.client.state.auth
        msisdn_880 = normalize_msisdn(msisdn or (auth.msisdn if auth else "8801"))
        return self.client.get_json(
            "POST", CAMPAIGN_ACTIVATE_ENDPOINT,
            json_body=campaign_activate_body(pack, msisdn_880),
            auth_mode=AuthMode.SUBSCRIBER,
        )

    def _purchase_headers(self, balance: dict[str, Any] | None = None) -> dict[str, str]:
        """X-Service-Class-A from balance; B party unknown for CLI purchases."""
        balance = balance if balance is not None else _balance_snapshot(self.client)
        service_class = balance.get("service_class")
        return {"X-Service-Class-A": str(service_class)} if service_class else {}
