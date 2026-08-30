"""Usage history and itemized-bill wire models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UsageHistoryItem(BaseModel):
    """One CDR entry (`UsageHistoryResponse.UsageHistoryItem`, subset displayed by the app).

    The backend types scalar fields inconsistently (ints for `usage_type`,
    `type`, nulls everywhere), so string fields coerce before validation.
    """

    model_config = ConfigDict(extra="allow")

    b_party: str = ""
    cdr_type: str = ""
    channel_source: str = ""
    consumed_usage: str = ""
    msisdn: str = ""
    offer_name: str = ""
    offer_validity: str = ""
    usage_charge: str = ""
    usage_date: str = ""  # dd-MM-yyyy on the wire
    usage_time: str = ""
    usage_type: str = ""  # "0" = outgoing, else incoming
    usage_flag: str = ""
    usage_flag_type: str = ""  # ribbon theme key: e.g. "ebadjust", "roaming"
    auto_renewal_flag: str = ""
    fnf_flag: str = ""
    source: str = ""
    timestamp: int = 0

    @field_validator("b_party", "cdr_type", "channel_source", "consumed_usage", "msisdn",
                     "offer_name", "offer_validity", "usage_charge", "usage_date",
                     "usage_time", "usage_type", "usage_flag", "usage_flag_type",
                     "auto_renewal_flag", "fnf_flag", "source", mode="before")
    @classmethod
    def _coerce_scalars(cls, value: Any) -> Any:
        return "" if value is None else str(value) if isinstance(value, (int, float)) else value

    @property
    def direction(self) -> str:
        return "out" if self.usage_type == "0" else "in"

    @property
    def charge(self) -> str:
        try:
            return f"{float(self.usage_charge):.2f}"
        except (TypeError, ValueError):
            return self.usage_charge or "0.00"


class UsageHistoryCategory(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = ""
    type: str = ""
    slug: str = ""  # e.g. voice-history, internet-history, recharge
    data: list[UsageHistoryItem] = Field(default_factory=list)

    @field_validator("title", "type", "slug", mode="before")
    @classmethod
    def _coerce_scalar(cls, value: Any) -> str:
        return "" if value is None else str(value)


class UsageHistoryResponse(BaseModel):
    """`GET /v2/usage_history?cdr_start_date=&cdr_end_date=`."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    cdr: list[UsageHistoryCategory] = Field(default_factory=list)
    menu: dict[str, Any] = Field(default_factory=dict)
    sub_menu: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict, alias="_meta")


class BillCycle(BaseModel):
    """One selectable postpaid bill cycle (computed client-side, app logic)."""

    invoice_month: str  # anchor date, yyyy-MM-dd — the value sent to the API
    start: str  # cycle start (anchor - 1 month), yyyy-MM-dd
    end: str  # cycle end (anchor - 1 day), yyyy-MM-dd
