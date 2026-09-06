"""Auth wire models — subscriber tokens and guest sessions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from gpcli.models.common import ErrorInfo


class Auth(BaseModel):
    """`model/auth/Auth.java` — the subscriber session token set."""

    model_config = ConfigDict(extra="allow")

    id: int = 0
    access_token: str = ""
    token: str = ""  # duplicate of access_token in server responses
    refresh_token: str = ""
    is_primary: int = 1
    ng: int = 0
    msisdn: str = ""
    expire_at: int | None = None
    created_at: int | None = None  # client-side issuance time (refresh rate-guard)

    def is_expired(self, now: int, skew: int = 600) -> bool:
        return self.expire_at is not None and now > self.expire_at - skew


class OtpResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    result: str | None = None
    error: ErrorInfo | None = None


class GuestLoginResponse(BaseModel):
    """POST /guest-login — anonymous OAuth credential issuance."""

    model_config = ConfigDict(extra="allow")

    user_id: str = Field(alias="userId")
    client_id: str = Field(alias="clientId")
    client_secret: str = Field(alias="clientSecret")
    error: ErrorInfo | None = None


class GuestTokenResponse(BaseModel):
    """POST apigw/oauth/v2/token (client_credentials)."""

    model_config = ConfigDict(extra="allow")

    status: str = ""
    access_token: str = Field(default="", alias="accessToken")
    expires_in: str = Field(default="", alias="expiresIn")
    scope: str = ""
    token_type: str = Field(default="", alias="tokenType")
    user_id: str = Field(default="", alias="userId")
    error: ErrorInfo | None = None

    @property
    def expires_in_seconds(self) -> int:
        try:
            return int(self.expires_in)
        except (TypeError, ValueError):
            return 3600


class GuestSession(BaseModel):
    """Persisted guest-mode session (anonymous, device-bound)."""

    user_id: str
    client_id: str
    client_secret: str
    access_token: str = ""
    issued_at: int = 0
    expires_at: int = 0  # issued_at + expiresIn

    def token_expired(self, now: int, skew: int = 60) -> bool:
        return bool(
            not self.access_token
            or (self.expires_at and now > self.expires_at - skew)
        )
