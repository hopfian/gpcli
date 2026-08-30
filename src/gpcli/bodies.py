"""Pure request-body builders for the MyGP wire formats.

Consolidates every body construction that mirrors a decompiled Java/Kotlin
builder — `Api.l()` (campaign-activate / pack_data), `MakePaymentBody`
(recharge_data) — so the exact wire literals live in one auditable place.
No I/O, no state: services import from here and stay thin.
"""

from __future__ import annotations

from typing import Any

from gpcli.models import PackItem
from gpcli.msisdn import local_msisdn


def pack_recharge_journey(pack: PackItem) -> dict[str, Any]:
    """The recharge_journey sub-object if the catalog carried one."""
    journey = pack.model_extra.get("recharge_journey") if pack.model_extra else None
    return journey if isinstance(journey, dict) else {}


def campaign_activate_body(pack: PackItem, msisdn: str) -> dict[str, Any]:
    """The app's `Api.l()` body (subset — required + common fields, faithful literals)."""
    body: dict[str, Any] = {
        "campaign_id": pack.keyword,
        "catalog_id": pack.id,
        "auto_renew": "1" if str(pack.additional_data.get("auto_renewal")) == "1" else "0",
        "is_biscuit_pack_journey": "0",
        "price": str(pack.price_value or 0),
        "price_vat": str(pack.price_value or 0),
        "recharge": str(pack.price_value or 0),
        "msisdn": msisdn or "0",
        "is_crm": "1",
        "eb": (
            "1"
            if "eb_eligible_offer" in pack.attributes and "data_loan_offer" not in pack.attributes
            else "0"
        ),
        "dynamic_eb": "0",
        "bonus_amount": "0",
    }
    return body


def build_recharge_data(
    *,
    amount: int,
    msisdn: str,
    provider: str,
    identifier: str,
    main_balance: str,
    eb_due: float,
    pack: PackItem | None = None,
) -> dict[str, Any]:
    """The `MakePaymentBody` dict — becomes `recharge_data` of recharge-and-activate."""
    body: dict[str, Any] = {
        "amount": str(amount),
        "recharge_msisdn": local_msisdn(msisdn),
        "service_provider": provider or None,
        "eb_due": eb_due,
        "campaign_code": None,
        "channel": None,
        "pack_name": None,
        "crm_keyword": None,
        "main_balance": main_balance,
        "identifier": identifier or None,
        "channel_code": None,
        "is_personalized": 0,
        "is_new_user": 0,
        "catalog_id": None,
        "card_id": None,
        "connection_type": "prepaid",
        "b_party_connection_type": None,
    }
    if pack is not None:
        # when a pack rides the recharge, PurchaseHelper copies pack fields in
        journey = pack_recharge_journey(pack)
        body.update({
            "campaign_code": pack.additional_data.get("recharge_campaign_id") or None,
            "channel": journey.get("sub_channel") or journey.get("subChannel") or None,
            "pack_name": pack.title,
            "crm_keyword": pack.keyword,
            "catalog_id": pack.id,
            "card_id": pack.additional_data.get("card_id") or None,
        })
    return body


def build_pack_data(
    pack: PackItem, msisdn: str, *, otp: str = "", recharge: int | None = None
) -> dict[str, Any]:
    """`pack_data` — the Api.l() body plus the RechargeAndActivateUseCase additions."""
    body: dict[str, Any] = {
        "campaign_id": pack.keyword,
        "catalog_id": pack.id,
        "auto_renew": "1" if str(pack.additional_data.get("auto_renewal")) == "1" else "0",
        "is_biscuit_pack_journey": "0",
        "price": str(pack.price_value or 0),
        "price_vat": str(pack.price_value or 0),
        "recharge": str(recharge if recharge is not None else (pack.price_value or 0)),
        "msisdn": msisdn or "0",
        "bonus_points": None,
        "bonus_points_amount": None,
        "content_source": "recharge_and_activate",
        "referral": None,
        "is_crm": "1",
        "eb": (
            "1"
            if "eb_eligible_offer" in pack.attributes and "data_loan_offer" not in pack.attributes
            else "0"
        ),
        "dynamic_eb": "0",
        "myplan_id": None,
        "service_class": None,
        "bonus_amount": "0",
        "recharge_transaction_id": None,
        "hash": None,
        "gift": None,
        "personalized_bonus": None,
        "card_id": pack.additional_data.get("card_id") or None,
    }
    # RechargeAndActivateUseCaseImpl.c() additions
    body["forced"] = "1"
    if otp:
        body["otp"] = otp
    return body
