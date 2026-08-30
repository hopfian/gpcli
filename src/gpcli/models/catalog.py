"""Catalog wire models — flexiplan, VAS, packs, CMP offers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FlexiMap(BaseModel):
    """Selectable option values (data/bioscope in MB; days = validity)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    days: list[int] = Field(default_factory=list)
    voice: list[int] = Field(default_factory=list)
    data: list[int] = Field(default_factory=list)
    data4g: list[int] = Field(default_factory=list, alias="4G")
    sms: list[int] = Field(default_factory=list)
    bioscope: list[int] = Field(default_factory=list)
    mca: list[int] = Field(default_factory=list)


class FlexiSelected(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    days: int = 0
    voice: int = 0
    data: int = 0
    data4g: int = Field(default=0, alias="4G")
    sms: int = 0
    bioscope: int = 0
    mca: int = 0


class FlexiPlan(BaseModel):
    """`GET catalogs/v2/flexiplans` — the build-your-own-bundle catalog."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    hash: str = ""
    mca_price: dict[str, float] = Field(default_factory=dict)
    mca_market_price: dict[str, float] = Field(default_factory=dict)
    vat: dict[str, float] = Field(default_factory=dict)
    map: FlexiMap = Field(default_factory=FlexiMap)
    selected: FlexiSelected = Field(default_factory=FlexiSelected)
    bundles: dict[str, str] = Field(default_factory=dict)
    elegible_options: dict[str, Any] = Field(default_factory=dict, alias="elegibleOptions")
    settings: dict[str, Any] = Field(default_factory=dict)


class FlexiBundlePrice(BaseModel):
    """Decoded `bundles` value (FlexiplanHelperKt.B): `B.._M.._C.._T.._P.._S.._D..`."""

    base_price: float = 0.0  # B
    market_price: float = 0.0  # M
    commission: float = 0.0  # C
    base_price_vat: float = 0.0  # T
    price_vat_mca_prepaid: float = 0.0  # P — final prepaid price incl. VAT (+MCA)
    price_vat_mca_postpaid: float = 0.0  # S
    discount_percent: int = 0  # D


class VasCategory(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    priority: int = 0


class VasService(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    service_id: str = ""
    category_id: int = 0
    price: str = ""
    price_unit: str = ""
    subscription_period: int = 0
    subscription_unit: str = ""
    registration_period: int = 0
    registration_unit: str = ""


class PackVolumeItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    value: str | None = None
    unit: str | None = None


class PackVolume(BaseModel):
    model_config = ConfigDict(extra="allow")

    internet: PackVolumeItem | None = None
    voice: PackVolumeItem | None = None
    sms: PackVolumeItem | None = None


class PackValidity(BaseModel):
    model_config = ConfigDict(extra="allow")

    value: str | None = None
    unit: str | None = None


class PackItem(BaseModel):
    """One entry of `GET v3/catalogs` `catalogs` — the app's pack model (subset).

    The backend types scalar fields inconsistently (price `150` vs `"150"`,
    null validity values), so string fields coerce numerics before validation.
    """

    model_config = ConfigDict(extra="allow")

    id: str = ""
    type: str = ""
    customer_type: str = ""
    title: str = ""
    keyword: str = ""
    price: str = ""
    validity: PackValidity | None = None
    volume: PackVolume | None = None
    attributes: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    eb_forward: int = 0
    purchase_with_account_balance: int = 0
    additional_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "type", "customer_type", "title", "keyword", "price", mode="before")
    @classmethod
    def _coerce_scalar(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)

    @field_validator("attributes", "filters", mode="before")
    @classmethod
    def _drop_null_tags(cls, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(v) for v in value if v is not None]

    @property
    def price_value(self) -> float | None:
        try:
            return float(self.price)
        except (TypeError, ValueError):
            return None

    def cashback_text(self) -> str:
        extra = self.additional_data or {}
        text = extra.get("cashback_text") or extra.get("dynamic_cashback_text") or ""
        if not text:
            digital = extra.get("digital_payment_cashback") or {}
            text = digital.get("text") or ""
        return str(text)

    def volume_summary(self) -> str:
        """`25 GB · 300 min · 100 sms` style summary."""
        parts: list[str] = []
        vol = self.volume
        if vol:
            for item in (vol.internet, vol.voice, vol.sms):
                if item and item.value and item.value not in ("0", "null"):
                    parts.append(f"{item.value} {item.unit or ''}".strip())
        return " · ".join(parts)

    def validity_summary(self) -> str:
        validity = self.validity
        if not validity:
            return ""
        if validity.value:
            return f"{validity.value} {validity.unit}".strip()
        return validity.unit


class CmpOffer(BaseModel):
    """One entry of `GET v2/cmp-offers` — personalized campaign offers."""

    model_config = ConfigDict(extra="allow")

    price: str = ""
    name: str = ""
    description: str = ""
    short_description: str = ""
    pack_type: str = ""
    keyword: str = ""
    campaign_id: str = ""
    is_campaign: int = 0
    type: str = ""
    catalog_pack_type: str = ""
    catalog_filter: list[str] = Field(default_factory=list)
    offers: list[dict[str, Any]] = Field(default_factory=list)
    reward: int = 0

    def offers_summary(self) -> str:
        parts = []
        for offer in self.offers:
            if isinstance(offer, dict) and offer.get("volume"):
                parts.append(str(offer["volume"]))
        return " · ".join(parts[:3])
