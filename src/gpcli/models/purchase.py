"""Purchase & recharge wire models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RechargeOffer(BaseModel):
    """`GET /recharge/offer` item — top-level JSON array."""

    model_config = ConfigDict(extra="allow")

    condition: str = ""
    text: str = ""
    type: str = ""


class PaymentHistoryItem(BaseModel):
    """`GET orders/v1/bill-payments` item."""

    model_config = ConfigDict(extra="allow")

    id: int | None = None
    amount: float | None = None
    date: str = ""
    time: str = ""
    type: str = ""
    unit: str = ""
    action: str = ""


class PaymentHistory(BaseModel):
    model_config = ConfigDict(extra="allow")

    result: list[PaymentHistoryItem] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class RechargeGatewayResult(BaseModel):
    """`POST /recharge` — per-MFS payment URLs consumed by a WebView."""

    model_config = ConfigDict(extra="allow")

    payment_url: str | None = None
    bkash_url: str | None = None
    rocket_url: str | None = None


class DirectRechargeData(BaseModel):
    model_config = ConfigDict(extra="allow")

    recharge_transaction_id: str = ""
    slug: str = ""
    dueAmount: str = ""
    rechargeAmount: int | None = None
    totalCampaignDiscount: Any = None
    serviceProvider: str = ""
    rechargeMsisdn: str = ""


class RechargeAndActivateData(BaseModel):
    """`POST /recharge-and-activate` -> data."""

    model_config = ConfigDict(extra="allow")

    status: str = ""
    url: dict[str, Any] | None = None  # {payment_url}
    direct_recharge: DirectRechargeData | None = None

    @property
    def payment_url(self) -> str:
        if isinstance(self.url, dict):
            return str(self.url.get("payment_url", "") or "")
        return ""


class RechargeAndActivateResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: RechargeAndActivateData | None = None
    pack: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return bool(
            self.data
            and self.data.status.lower() in ("success", "pending")
        )

    @property
    def action_required(self) -> bool:
        return bool(self.data and self.data.status.lower() == "action_required")


class MakePaymentResult(BaseModel):
    """`POST /payment-gateway/payment` — success only when status == "success"."""

    model_config = ConfigDict(extra="allow")

    code: int | None = None
    status: str = ""
    data: dict[str, Any] = Field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status.lower() == "success"
