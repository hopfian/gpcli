"""Authentication flows — OTP, silent SIM, guest, refresh, logout.

Wire-verified against MyGP 5.31.0.
"""

from __future__ import annotations

import contextlib
import time

import httpx

from gpcli.client import AuthMode, MyGPClient
from gpcli.constants import (
    GUEST_LOGIN_ENDPOINT,
    GUEST_OAUTH_TOKEN_URL,
    LOGOUT_ALL_ENDPOINT,
    LOGOUT_ENDPOINT,
    MSISDN_ENDPOINT,
    MYGP_APP_VERSION,
    OTP_LOGIN_ENDPOINT,
    SILENT_CODE_ENDPOINT,
    SILENT_VERIFY_ENDPOINT,
)
from gpcli.crypto import build_silent_login, silent_login_body
from gpcli.errors import (
    ApiError,
    AuthRequiredError,
    GuestFlowError,
    SilentLoginUnavailable,
)
from gpcli.models import (
    Auth,
    GuestLoginResponse,
    GuestSession,
    GuestTokenResponse,
    OtpResponse,
    error_from_payload,
)
from gpcli.msisdn import normalize_msisdn
from gpcli.state import apply_new_auth

__all__ = ["AuthService", "normalize_msisdn"]


class AuthService:
    def __init__(self, client: MyGPClient):
        self.client = client

    # ------------------------------------------------------------------ OTP

    def send_otp(self, msisdn: str) -> OtpResponse:
        """`GET v2/otp-login?msisdn=` — triggers SMS dispatch; stages the msisdn."""
        normalized = normalize_msisdn(msisdn)
        data = self.client.get_json(
            "GET", OTP_LOGIN_ENDPOINT,
            params={"msisdn": normalized},
            auth_mode=AuthMode.NONE,
        )
        if isinstance(data, dict) and data.get("result") == "success":
            self.client.state.staged_msisdn = normalized
            self.client.state.save()
        return OtpResponse.model_validate(data)

    def verify_otp(self, otp: str, *, msisdn: str | None = None) -> Auth:
        """`POST v2/otp-login` — exchange the SMS code for tokens."""
        normalized = msisdn or self.client.state.staged_msisdn
        if not normalized:
            raise AuthRequiredError("no OTP in flight — run `gpcli auth send-otp <msisdn>` first")
        state = self.client.state
        body = {
            "msisdn": normalized,
            "otp": otp.strip(),
            "app_version": MYGP_APP_VERSION,
            "device_id": state.device.device_id,
            "device_model": state.device.device_model,
            "device_name": state.device.device_name,
        }
        data = self.client.get_json(
            "POST", OTP_LOGIN_ENDPOINT, json_body=body, auth_mode=AuthMode.NONE
        )
        auth = Auth.model_validate(data)
        if auth.access_token == "":
            raise ApiError(None, "OTP verification returned no access token")
        auth.msisdn = auth.msisdn or normalized
        apply_new_auth(state, auth)
        state.staged_msisdn = None
        state.save()
        return auth

    # -------------------------------------------------------------- silent

    def network_msisdn(self) -> str | None:
        """`GET /msisdn` — carrier-network-derived number (GP mobile data only)."""
        try:
            data = self.client.get_json("GET", MSISDN_ENDPOINT, auth_mode=AuthMode.NONE)
        except ApiError:
            return None
        if isinstance(data, dict):
            for key in ("msisdn", "data", "result"):
                if isinstance(data.get(key), str):
                    return data[key]
        return None

    def silent_login(self) -> Auth:
        """`GET /code` -> AES-CTR challenge -> `POST /v2/code`.

        Requires a Grameenphone mobile-data connection; the nginx edge
        returns 403 HTML from any other network.
        """
        state = self.client.state
        response = self.client.request("GET", SILENT_CODE_ENDPOINT, auth_mode=AuthMode.NONE)
        if response.status_code == 403:
            raise SilentLoginUnavailable(
                "silent login is only available from Grameenphone mobile data "
                "(the /code endpoint is IP-gated by the carrier edge)"
            )
        data = response.json()
        if err := error_from_payload(data):
            raise ApiError(err.code, err.summary(), err.description)
        server_code = data.get("code") if isinstance(data, dict) else None
        if not server_code:
            raise SilentLoginUnavailable(f"unexpected /code response: {data!r}")

        spec = build_silent_login(state.device.device_id, str(server_code))
        body = silent_login_body(
            spec,
            app_version=MYGP_APP_VERSION,
            device_model=state.device.device_model,
            device_name=state.device.device_name,
        )
        data = self.client.get_json(
            "POST", SILENT_VERIFY_ENDPOINT, json_body=body, auth_mode=AuthMode.NONE
        )
        auth = Auth.model_validate(data)
        if auth.access_token == "":
            raise ApiError(None, "silent login returned no access token")
        apply_new_auth(state, auth)
        state.save()
        return auth

    # --------------------------------------------------------------- guest

    def guest_login(self, *, refresh_token: bool = False) -> GuestSession:
        """Full anonymous flow: /guest-login -> apigw OAuth client_credentials.

        `refresh_token=True` re-mints the OAuth access token for an existing
        guest identity (they expire after ~1h).
        """
        state = self.client.state
        guest = state.guest
        now = int(time.time())

        if guest is None or guest.client_id == "":
            data = self.client.get_json(
                "POST", GUEST_LOGIN_ENDPOINT,
                json_body={
                    "deviceId": state.device.device_id,
                    # the app sends the Google Advertising ID here; the server
                    # rejects a null aaId (402 "failed") but accepts any UUID.
                    "aaId": state.device.device_id + "-0000-4000-8000-" + state.device.device_id,
                },
                auth_mode=AuthMode.NONE,
            )
            login = GuestLoginResponse.model_validate(data)
            if not login.user_id:
                raise GuestFlowError("guest-login did not issue a userId")
            guest = GuestSession(
                user_id=login.user_id,
                client_id=login.client_id,
                client_secret=login.client_secret,
            )

        if refresh_token or guest.token_expired(now):
            try:
                token_response = self.client.raw_post(
                    GUEST_OAUTH_TOKEN_URL,
                    data={
                        "client_id": guest.client_id,
                        "client_secret": guest.client_secret,
                        "grant_type": "client_credentials",
                        "userId": guest.user_id,  # NOT user_id — the app sends the literal form field
                    },
                    headers={
                        "User-Agent": self.client.user_agent,
                        "Accept-Language": state.language,
                    },
                )
                data = token_response.json()
            except httpx.HTTPError as err:
                raise GuestFlowError(f"guest token request failed: {err}") from err
            if err := error_from_payload(data):
                raise GuestFlowError(f"guest token minting failed: [{err.code}] {err.summary()}")
            token = GuestTokenResponse.model_validate(data)
            if token.access_token == "":
                raise GuestFlowError("guest token endpoint returned no accessToken")
            guest.access_token = token.access_token
            guest.issued_at = now
            guest.expires_at = now + token.expires_in_seconds

        state.guest = guest
        state.save()
        return guest

    # -------------------------------------------------------- lifecycle

    def refresh(self, *, force: bool = False) -> Auth:
        return self.client.refresh_auth(force=force)

    def logout(self, *, all_devices: bool = False) -> None:
        """Invalidate the session server-side and clear local state."""
        endpoint = LOGOUT_ALL_ENDPOINT if all_devices else LOGOUT_ENDPOINT
        auth = self.client.state.auth
        if auth and auth.access_token:
            with contextlib.suppress(ApiError, AuthRequiredError):
                self.client.request("GET", endpoint, auth_mode=AuthMode.SUBSCRIBER)
        self.client.state.auth = None
        self.client.state.save()
