"""Partner-service wire models — token envelopes for deeplink partners."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PartnerServiceToken(BaseModel):
    """`POST services/v1/partners/{slug}/get-token` responses (deen/win)."""

    model_config = ConfigDict(extra="allow")

    token: str = ""
    url: str = ""
    type: str = ""
    customer_id: str = ""
    token_info: dict[str, Any] = Field(default_factory=dict)


class PartnerToken(BaseModel):
    """Generic partner token (chatbot: `POST services/v1/partners/chatbot/get-token`)."""

    model_config = ConfigDict(extra="allow")

    token: str = ""
    token_info: dict[str, Any] = Field(default_factory=dict)
