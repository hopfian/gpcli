"""Comms wire models — SIM, FnF, welcome tunes, gifts, GA/balance status."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SimOwnershipCertificate(BaseModel):
    """`GET /v1/ownership-certificate` — `data` is the certificate as HTML."""

    model_config = ConfigDict(extra="allow")

    status: str = ""
    data: str = ""

    @property
    def ok(self) -> bool:
        return self.status.lower() == "success"


class BiometricDocType(BaseModel):
    """`GET /v1/customers/get-id-document`."""

    model_config = ConfigDict(extra="allow")

    data: dict[str, Any] = Field(default_factory=dict)

    @property
    def doc_type(self) -> str:
        return str(self.data.get("doc_type", ""))


class BiometricSim(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str = ""
    masking: str = ""
    msisdn: str = ""
    operator: str = ""
    status: str = ""


class BiometricSimList(BaseModel):
    """`POST /v2/customers/biometric-msisdn` — active/bondho/other-operator SIMs."""

    model_config = ConfigDict(extra="allow")

    data: dict[str, Any] = Field(default_factory=dict)

    def _sims(self, key: str) -> list[BiometricSim]:
        return [BiometricSim.model_validate(s) for s in self.data.get(key, []) or []]

    @property
    def active_sims(self) -> list[BiometricSim]:
        return self._sims("active_sim_list")

    @property
    def bondho_sims(self) -> list[BiometricSim]:
        return self._sims("bondho_sim_list")

    @property
    def other_operator_sims(self) -> list[BiometricSim]:
        return self._sims("other_operator_sim_list")


class FnfItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    fnf: str = ""
    requestdate: str = ""
    changedate: str = ""


class FnfInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    product: str = ""
    totalnormalFnF: int = 0
    totalsuperFnF: int = 0
    usednormalFnF: int = 0
    usedsuperFnF: int = 0

    @property
    def used_total(self) -> int:
        return self.usednormalFnF + self.usedsuperFnF

    @property
    def total(self) -> int:
        return self.totalnormalFnF + self.totalsuperFnF


class FnfList(BaseModel):
    """`GET /fnf-list` — note the app's literal (inconsistent) field names."""

    model_config = ConfigDict(extra="allow")

    normal_fnf: list[FnfItem] = Field(default_factory=list)
    super_fnf: list[FnfItem] = Field(default_factory=list)
    info: FnfInfo | None = None


class WelcomeTune(BaseModel):
    """`WelcomeTune.java` — plain field names (PascalCase on the wire)."""

    model_config = ConfigDict(extra="allow")

    Price: float | None = None
    SingerName: str = ""
    ToneCode: str = ""
    ToneName: str = ""
    ToneValidDay: int | None = None


class ReceiverGift(BaseModel):
    """`GET /v1/customers/gifts` item."""

    model_config = ConfigDict(extra="allow")

    title: str = ""
    sender_name: str = ""
    receiver: str = ""
    price: str = ""
    pack_type: str = ""
    validity: str = ""
    transaction_id: str = ""
    message: str = ""


class GAOfferInfo(BaseModel):
    """`GET /ga-offer-details` value — GA (gross add-on / new SIM) usage."""

    model_config = ConfigDict(extra="allow")

    is_current_month_availed: int = -1
    remaining: int = -1
    total_campaign_period: int = -1


class BalanceStatusItem(BaseModel):
    """`GET /balance-status` item (internet/voice lists)."""

    model_config = ConfigDict(extra="allow")

    name: str = ""
    product_short_code: str = ""
    auto_renew_status: int | None = None
    auto_renew_date: str = ""
    activation_date: str = ""
    da: str | None = None
    pack_text: str = ""
    usage: dict[str, Any] | None = None
