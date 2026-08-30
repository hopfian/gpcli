"""HTTP client replicating MyGP's OkHttp interceptor stack.

Interceptor semantics being emulated (decoded from the decompiled app):

* **UserAgentInterceptor** — every request gets
  ``User-Agent: Android/{sdk} MyGP/{code} ({lang})``, ``Accept-Language``,
  ``Vary``, ``APP-MSISDN`` / ``APP-MSISDN-OLD``, ``X-REFERENCE-ID``
  (= device id), ``ng`` header, and ``?lang=&ng=`` query params.

* **AuthInterceptor** — requests to the legacy gateway carrying a subscriber
  token get ``Authorization: Bearer <access_token>`` and ``?id=<auth.id>``
  (except ``v2/sbcontents/*`` paths). A **403** triggers one silent
  refresh + retry; **401 / 911 / 410** invalidate the session.

* **Refresh rate-guard** — the app skips refreshes for tokens younger than
  600s and proactively refreshes when within 600s of expiry.

Guest-mode requests (Apigee) carry the guest bearer plus the literal
``userId`` header (the value of `SMTInboxConstants.API_KEY_USER_ID`).
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from enum import Enum
from typing import Any, Protocol

import httpx

from gpcli.constants import (
    BASES,
    ID_PARAM_SKIP_MARKERS,
    REFRESH_ENDPOINT_GP,
    REFRESH_ENDPOINT_NON_GP,
    REFRESH_MIN_AGE,
    TOKEN_EXPIRY_SKEW,
    build_user_agent,
)
from gpcli.errors import ApiError, AuthExpiredError, AuthRequiredError
from gpcli.models import Auth, error_from_payload
from gpcli.state import State, apply_new_auth


class AuthMode(str, Enum):
    """How a request authenticates. Members ARE plain strings (str mixin)."""

    AUTO = "auto"  # subscriber if available, else guest, else anonymous
    SUBSCRIBER = "subscriber"
    GUEST = "guest"
    NONE = "none"


class ApiCaller(Protocol):
    """Structural interface for everything a service may touch on a client.

    `MyGPClient` satisfies this without inheritance (structural typing);
    services accept it instead of the concrete class so tests can substitute
    doubles. `AuthService` additionally needs the raw transport and stays on
    the concrete `MyGPClient`.
    """

    @property
    def state(self) -> State: ...

    @property
    def user_agent(self) -> str: ...

    def request(
        self,
        method: str,
        path: str,
        *,
        base: str = "mygpapi",
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_mode: str = AuthMode.AUTO,
    ) -> httpx.Response: ...

    def get_json(
        self,
        method: str,
        path: str,
        *,
        base: str = "mygpapi",
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_mode: str = AuthMode.AUTO,
    ) -> Any: ...

    def refresh_auth(self, *, force: bool = False) -> Auth: ...


class MyGPClient:
    """Stateful API client. One instance per process; reuse for connection pooling."""

    def __init__(self, state: State, *, timeout: float = 30.0, transport: httpx.BaseTransport | None = None):
        self.state = state
        self._http = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._http.close()

    def raw_post(
        self,
        url: str,
        *,
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Raw POST outside the interceptor stack (Apigee OAuth minting).

        Only for endpoints that must NOT receive the MyGP headers/params —
        e.g. `oauth/v2/token`, where the app's own OkHttp call is plain too.
        """
        request = self._http.build_request("POST", url, data=data, headers=headers)
        return self._http.send(request)

    def __enter__(self) -> MyGPClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ URL

    @staticmethod
    def resolve_url(base: str, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        try:
            root = BASES[base]
        except KeyError as err:
            raise ValueError(f"unknown base {base!r}; expected one of {sorted(BASES)}") from err
        if not path.startswith("/"):
            path = "/" + path
        return root + path

    # --------------------------------------------------------------- tokens

    def _active_auth(self) -> Auth | None:
        auth = self.state.auth
        if auth and auth.access_token:
            return auth
        return None

    def _refresh_allowed(self, auth: Auth, now: int | None = None) -> bool:
        """App guard: never refresh tokens younger than REFRESH_MIN_AGE."""
        now = now if now is not None else int(time.time())
        if auth.refresh_token == "":
            return False
        return not (auth.created_at is not None and now < auth.created_at + REFRESH_MIN_AGE)
    def refresh_auth(self, *, force: bool = False) -> Auth:
        """Api.M() — POST refresh-token endpoint, promote new tokens, persist."""
        auth = self._active_auth()
        if auth is None:
            raise AuthRequiredError("no subscriber session to refresh")
        now = int(time.time())
        if not force and not self._refresh_allowed(auth, now):
            return auth

        endpoint = REFRESH_ENDPOINT_NON_GP if auth.ng else REFRESH_ENDPOINT_GP
        # The app fires this through the same interceptor stack, i.e. with the
        # (possibly stale) bearer + id param attached.
        response = self._send(
            "POST",
            self.resolve_url("mygpapi", endpoint),
            json_body={"refresh_token": auth.refresh_token},
            auth_token=auth,
        )
        data = self._decode(response)
        if err := error_from_payload(data):
            raise ApiError(err.code, err.summary(), err.description)
        new_auth = Auth.model_validate(data)
        if new_auth.access_token == "":
            raise ApiError(None, "refresh endpoint returned no access token")
        new_auth.msisdn = new_auth.msisdn or auth.msisdn
        new_auth.id = new_auth.id or auth.id
        apply_new_auth(self.state, new_auth)
        self.state.save()
        return new_auth

    def _ensure_fresh_auth(self) -> Auth:
        """Proactive refresh when within TOKEN_EXPIRY_SKEW of expiry."""
        auth = self._active_auth()
        if auth is None:
            raise AuthRequiredError("not logged in — run `gpcli login <msisdn>`")
        now = int(time.time())
        if auth.is_expired(now, TOKEN_EXPIRY_SKEW) and self._refresh_allowed(auth, now):
            try:
                return self.refresh_auth()
            except (ApiError, httpx.HTTPError):
                return self._active_auth() or auth  # let the request fail naturally
        return auth

    # ------------------------------------------------------------- request

    @property
    def user_agent(self) -> str:
        return build_user_agent(self.state.language)

    def _base_headers(self, auth: Auth | None) -> dict[str, str]:
        msisdn = auth.msisdn if auth else (self.state.staged_msisdn or "")
        return {
            "User-Agent": self.user_agent,
            "Accept-Language": self.state.language,
            "Vary": "Accept-Language",
            "X-REFERENCE-ID": self.state.device.device_id,
            "APP-MSISDN": msisdn,
            "APP-MSISDN-OLD": "",
            "ng": self.state.ng,
        }

    def _auth_headers(self, auth: Auth, url: str) -> dict[str, str]:
        if not url.startswith(BASES["mygpapi"]):
            return {}
        return {"Authorization": f"Bearer {auth.access_token}"}

    def _guest_headers(self) -> dict[str, str]:
        guest = self.state.guest
        if guest is None or guest.access_token == "":
            return {}
        return {
            "Authorization": f"Bearer {guest.access_token}",
            "userId": guest.user_id,
            "Cache-Control": "no-cache",
        }

    def _base_params(self, auth: Auth | None, url: str) -> dict[str, str]:
        params: dict[str, str] = {"lang": self.state.language, "ng": self.state.ng}
        if (
            auth is not None
            and url.startswith(BASES["mygpapi"])
            and not any(marker in url for marker in ID_PARAM_SKIP_MARKERS)
        ):
            params["id"] = str(auth.id)
        return params

    def _send(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_token: Auth | None = None,
    ) -> httpx.Response:
        merged_headers: dict[str, str] = {}
        merged_params: dict[str, Any] = dict(params or {})

        merged_headers.update(self._base_headers(auth_token))
        if auth_token is not None:
            merged_headers.update(self._auth_headers(auth_token, url))
        merged_params.update(self._base_params(auth_token, url))
        if headers:
            merged_headers.update(headers)

        request = self._http.build_request(
            method.upper(), url, params=merged_params or None,
            json=json_body, data=data, headers=merged_headers,
        )
        return self._http.send(request)

    def request(
        self,
        method: str,
        path: str,
        *,
        base: str = "mygpapi",
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_mode: str = AuthMode.AUTO,
    ) -> httpx.Response:
        """Send a request with full interceptor emulation.

        Returns the raw `httpx.Response`; raises `AuthExpiredError` when the
        server invalidates the session, and `ApiError` never (envelopes are
        the caller's business — use `get_json` for that).
        """
        url = self.resolve_url(base, path)

        # --- resolve auth mode
        if auth_mode == AuthMode.NONE:
            token: Auth | None = None
            guest_headers: dict[str, str] = {}
        elif auth_mode == AuthMode.GUEST:
            token = None
            guest_headers = self._guest_headers()
            if not guest_headers:
                raise AuthRequiredError("no guest session — run `gpcli guest` first")
        elif auth_mode == AuthMode.SUBSCRIBER:
            token = self._ensure_fresh_auth()
            guest_headers = {}
        else:  # AUTO
            token = self._active_auth()
            if token is not None:
                token = self._ensure_fresh_auth()
            guest_headers = {} if token is not None else self._guest_headers()

        # --- first attempt
        merged = dict(headers or {})
        merged.update(guest_headers)
        response = self._send(method, url, params=params, json_body=json_body, data=data,
                              headers=merged or None, auth_token=token)

        # --- AuthInterceptor: 403 -> silent refresh + single retry
        if (
            response.status_code == 403
            and token is not None
            and url.startswith(BASES["mygpapi"])
            and self._refresh_allowed(token)
        ):
            try:
                token = self.refresh_auth()
            except (ApiError, httpx.HTTPError):
                token = None
            if token is not None:
                response = self._send(method, url, params=params, json_body=json_body,
                                      data=data, headers=headers, auth_token=token)

        # --- AuthInterceptor: 401/911/410 -> session invalid, forced logout
        if token is not None and response.status_code in (401, 410, 911):
            self.state.auth = None
            self.state.save()
            raise AuthExpiredError(
                f"session rejected (HTTP {response.status_code}) — logged out, "
                "run `gpcli login <msisdn>` to sign in again"
            )

        return response

    # -------------------------------------------------------------- helpers

    @staticmethod
    def _decode(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as err:
            raise ApiError(
                response.status_code,
                f"non-JSON response from {response.request.url}",
                response.text[:200],
            ) from err

    def get_json(
        self,
        method: str,
        path: str,
        *,
        base: str = "mygpapi",
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        data: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        auth_mode: str = AuthMode.AUTO,
    ) -> Any:
        """`request(...)` + JSON decode; raises `ApiError` on ErrorV2 envelopes."""
        response = self.request(
            method, path, base=base, params=params, json_body=json_body,
            data=data, headers=headers, auth_mode=auth_mode,
        )
        data = self._decode(response)
        if err := error_from_payload(data):
            raise ApiError(err.code, err.summary(), err.description)
        return data
