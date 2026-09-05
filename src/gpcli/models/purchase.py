"""Purchase & recharge wire models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    transaction_id: str | None = None  # server-generated, observed live
    campaign_code: str | None = None  # e.g. "Manualmygpp40,TMBasic5Dec"


class PaymentMethodItem(BaseModel):
    """`GET v2/payment-methods` item — a bindable payment method."""

    model_config = ConfigDict(extra="allow")

    name: str = ""
    payment_method_id: str = ""  # e.g. "nagad" — the bind path segment
    card_image: str = ""
    deeplink: str = ""  # mygp.grameenphone.com/mygp/connect_payment_method/<id>
    multiple_bind_support: int = 0
    unbind_message_key: str = ""
    payment_method_selection_title_key: str = ""
    is_active: bool | None = None


class PaymentMethodBindData(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str | None = None  # the provider's auth page (Nagad/bKash/card)


class PaymentMethodBindResponse(BaseModel):
    """`POST payment-gateway/bind/{id}` — data.url opens in the app's WebView."""

    model_config = ConfigDict(extra="allow")

    status: str | None = None
    code: int | None = None
    data: PaymentMethodBindData | None = None

    @property
    def url(self) -> str:
        return self.data.url if self.data and self.data.url else ""


class DirectRechargeData(BaseModel):
    model_config = ConfigDict(extra="allow")

    recharge_transaction_id: str = ""
    slug: str = ""
    dueAmount: str = ""
    rechargeAmount: int | None = None
    totalCampaignDiscount: Any = None
    serviceProvider: str = ""
    rechargeMsisdn: str = ""

    @field_validator("recharge_transaction_id", "slug", "dueAmount", "serviceProvider",
                     "rechargeMsisdn", mode="before")
    @classmethod
    def _coerce_scalars(cls, value: Any) -> Any:
        # the backend sends numeric fields as ints despite the String schema
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value)
        return value


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
