"""Common wire envelope — the ErrorV2 shape shared by every endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorInfo(BaseModel):
    """ErrorV2.Error (subset that appears on the wire)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    code: int | str | None = None
    reason: str | None = None
    message: str | None = None
    description: str | None = None
    status: str | None = None
    handel_from_interceptor: bool | None = Field(default=None, alias="handelFromInterceptor")

    def summary(self) -> str:
        return self.message or self.reason or self.description or "unknown error"


def error_from_payload(data: Any) -> ErrorInfo | None:
    """Extract an ErrorV2 envelope from a decoded response body, if present."""
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        payload = dict(data["error"])
        if data.get("status") == "failed" and "status" not in payload:
            payload.setdefault("status", "failed")
        return ErrorInfo.model_validate(payload)
    return None
