"""AutoPay wire models — products, settings, active subscriptions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AutoPayProduct(BaseModel):
    """`AutoPaySettings.products[]` — server-driven product configuration."""

    model_config = ConfigDict(extra="allow")

    credit_amount: str | None = None
    frequency: list[str] = Field(default_factory=list)
    frequency_unit: str | None = None
    product_code: str | None = None
    product_type: str | None = None
    title: str | None = None
    trigger_amount: str | None = None


class AutoPaySettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    autopay_blocked_amount: list[str] = Field(default_factory=list)
    autopay_postpaid_max_amount: str | None = None
    autopay_postpaid_min_amount: str | None = None
    autopay_prepaid_max_amount: str | None = None
    autopay_prepaid_min_amount: str | None = None
    autopay_card_max_amount: str | None = None
    autopay_card_min_amount: str | None = None
    autopay_setup_limit: str | None = None
    autopay_suggested_recharge_amount: list[str] = Field(default_factory=list)
    products: list[AutoPayProduct] = Field(default_factory=list)
    tutorial_url: str | None = None


class AutoPaymentInfo(BaseModel):
    """One active auto-payment subscription."""

    model_config = ConfigDict(extra="allow")

    id: int = 0
    msisdn: str = ""
    amount: str = ""
    frequency: str = ""
    frequency_unit: str = ""
    product_code: str = ""
    product_type: str = ""
    next_schedule_date: str = ""
    service_provider: str = ""
    service_provider_identifier: str = ""


class AutoPayListResponse(BaseModel):
    """Unwrapped `BaseResponse.data` of `GET v1/auto-payment/subscription-list`."""

    model_config = ConfigDict(extra="allow")

    setting: AutoPaySettings | None = None
    subscription: list[AutoPaymentInfo] = Field(default_factory=list)

    @property
    def products(self) -> list[AutoPayProduct]:
        return self.setting.products if self.setting else []
