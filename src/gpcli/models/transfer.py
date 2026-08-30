"""Balance-transfer wire models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BalanceTransferResponse(BaseModel):
    """`BalanceTransferResponse.java` — {status, result, message} envelope."""

    model_config = ConfigDict(extra="allow")

    status: int | None = None
    result: str = ""
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.result.lower() == "success"


class PinResetInitiateData(BaseModel):
    model_config = ConfigDict(extra="allow")

    otp_type: str | None = None
    reference_id: str | None = None
