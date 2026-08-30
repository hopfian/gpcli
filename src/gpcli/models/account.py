"""Account wire models — profile, identity, balances, emergency balance."""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from gpcli.models.common import ErrorInfo


class Profile(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = ""
    msisdn: str = ""
    name: str = ""
    profile_picture: str = ""
    email: str = ""
    gender: str = ""
    birthday: str = ""
    nid_dob: str = ""
    address: str = ""
    connectid_sub: str = ""
    multi_login: str = ""
    status: str = ""
    source: str = ""
    created_at: str = ""
    updated_at: str = ""


class Me(BaseModel):
    """GET /me — subscriber identity."""

    model_config = ConfigDict(extra="allow")

    msisdn: str = ""
    login_method: str = ""
    link_type: int = 0
    parent_msisdn: str | None = None
    profile: Profile | None = None


class UsageDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: int = 0
    label: str = ""
    value: str = ""
    unit: str = ""
    custom_label: str = ""


class EmergencyBalance(BaseModel):
    """`EmergencyBalance.java` — plain field names, no SerializedName.

    `GET /emergency-balance` returns {value, validity, …}; the full state
    (due/total/opt-in flags) lives in `GET /balance`'s nested object.
    """

    model_config = ConfigDict(extra="allow")

    balance: float = 0.0
    data_loan: float = 0.0
    due: float = 0.0
    dynamic_eb_limit: int = 0
    expiry: str = ""
    is_eb_opt_in: int = 0
    is_eb_pack_eligible: int = 0
    remaining: str = ""
    total: float = 0.0
    validity: str = ""
    value: float = 0.0

    @property
    def total_due(self) -> float:
        """`getTotalEmergencyBalance()` = ceil(max(due,0) + max(data_loan,0))."""
        return math.ceil(max(self.due, 0.0) + max(self.data_loan, 0.0))


class Balance(BaseModel):
    """GET /balance — main + package balances (subset; everything else passthrough)."""

    model_config = ConfigDict(extra="allow")

    balance: float = 0.0
    service_class: int = 0
    type: str = ""
    is_bs_user: bool = False
    emergency_balance: EmergencyBalance | None = None
    internet_details: UsageDetail | None = None
    sms_details: UsageDetail | None = None
    expiry: dict[str, Any] | None = None
    internet_packs: list[dict[str, Any]] = Field(default_factory=list)
    sms_packs: list[dict[str, Any]] = Field(default_factory=list)
    error: ErrorInfo | None = None
