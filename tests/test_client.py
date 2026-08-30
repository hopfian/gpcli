"""Client interceptor-emulation semantics (MockTransport)."""

import json
import time

import pytest
from constants import AUTH_ID, DEVICE_ID, MSISDN_880

from gpcli.client import AuthMode, MyGPClient
from gpcli.constants import BASE_MYGPAPI
from gpcli.errors import ApiError, AuthExpiredError, AuthRequiredError


def _sent(rec, i):
    return rec.requests[i]


class TestRequestAssembly:
    def test_resolve_url_normalizes_leading_slash(self):
        assert MyGPClient.resolve_url("mygpapi", "balance") == f"{BASE_MYGPAPI}/balance"
        assert MyGPClient.resolve_url("mygpapi", "/balance") == f"{BASE_MYGPAPI}/balance"
        assert MyGPClient.resolve_url("apigw", "/oauth") == "https://apigw.grameenphone.com/oauth"
        assert MyGPClient.resolve_url("mygpapi", "https://x.dev/y") == "https://x.dev/y"
        with pytest.raises(ValueError):
            MyGPClient.resolve_url("bogus", "/x")

    def test_subscriber_headers_and_id_param(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/me", json={"msisdn": MSISDN_880})
        client.get_json("GET", "/me", auth_mode=AuthMode.SUBSCRIBER)

        req = rec.requests[0]
        assert req.headers["Authorization"] == "Bearer TOKEN-A"
        assert req.url.params["id"] == str(AUTH_ID)
        assert req.url.params["lang"] == "en"
        assert req.url.params["ng"] == "0"
        assert req.headers["X-REFERENCE-ID"] == DEVICE_ID
        assert req.headers["APP-MSISDN"] == MSISDN_880
        assert req.headers["User-Agent"] == "Android/34 MyGP/530 (en)"
        assert req.headers["Vary"] == "Accept-Language"

    def test_id_param_skipped_for_sbcontents(self, make_client):
        client, rec = make_client()
        rec.add("GET", "v2/sbcontents/search", json={})
        client.get_json("GET", "/v2/sbcontents/search?q=x", auth_mode=AuthMode.SUBSCRIBER)
        assert "id" not in rec.requests[0].url.params

    def test_no_auth_when_auth_mode_none(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/guest-login", json={"userId": "1"})
        client.get_json("GET", "/guest-login", auth_mode=AuthMode.NONE)
        req = rec.requests[0]
        assert "Authorization" not in req.headers
        assert "id" not in req.url.params

    def test_guest_mode_requires_session(self, make_client):
        client, _ = make_client()
        with pytest.raises(AuthRequiredError):
            client.request("GET", "https://apigw.grameenphone.com/mygp/v1/cards", auth_mode=AuthMode.GUEST)

    def test_guest_headers(self, make_client, state):
        from gpcli.models import GuestSession

        state.guest = GuestSession(
            user_id="156530159", client_id="c", client_secret="s",
            access_token="GUESTTOK", issued_at=int(time.time()), expires_at=int(time.time()) + 3600,
        )
        client, rec = make_client()
        rec.add("GET", "/mygp/v1/cards", json={})
        client.get_json("GET", "https://apigw.grameenphone.com/mygp/v1/cards", auth_mode=AuthMode.GUEST)
        req = rec.requests[0]
        assert req.headers["Authorization"] == "Bearer GUESTTOK"
        assert req.headers["userId"] == "156530159"

    def test_msisdn_body_format(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/v2/otp-login", json={"result": "success"})
        client.get_json(
            "POST", "/v2/otp-login", auth_mode=AuthMode.NONE,
            json_body={"msisdn": MSISDN_880, "otp": "1234", "app_version": "5.31.0",
                       "device_id": DEVICE_ID, "device_model": "Pixel 8", "device_name": "Google"},
        )
        body = json.loads(rec.requests[0].content)
        assert body["msisdn"] == MSISDN_880
        assert body["app_version"] == "5.31.0"


class TestErrorSemantics:
    def test_error_envelope_raises_api_error(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"error": {"code": 402, "description": "failed"}})
        with pytest.raises(ApiError) as err:
            client.get_json("GET", "/balance", auth_mode=AuthMode.SUBSCRIBER)
        assert "402" in str(err.value)

    def test_401_clears_auth_and_raises(self, make_client, state):
        client, rec = make_client()
        rec.add("GET", "/me", status_code=401, json={"error": {"code": 401, "message": "Session expired"}})
        with pytest.raises(AuthExpiredError):
            client.request("GET", "/me", auth_mode=AuthMode.SUBSCRIBER)
        assert state.auth is None

    def test_911_and_410_logout_too(self, make_client, state):
        for code in (911, 410):
            from gpcli.models import Auth

            state.auth = Auth(id=1, access_token="T", refresh_token="R", created_at=int(time.time()) - 99999)
            client, rec = make_client()
            rec.add("GET", "/me", status_code=code, json={})
            with pytest.raises(AuthExpiredError):
                client.request("GET", "/me", auth_mode=AuthMode.SUBSCRIBER)
            assert state.auth is None

    def test_401_without_auth_returns_response(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/v2/otp-login", status_code=401, json={"error": {"code": 401, "message": "bad otp"}})
        # AuthMode.NONE -> no session to invalidate, envelope handled by caller
        response = client.request("GET", "/v2/otp-login", auth_mode=AuthMode.NONE)
        assert response.status_code == 401


class TestRefreshFlow:
    def test_403_triggers_refresh_and_retry(self, make_client, state):
        client, rec = make_client()
        rec.add("GET", "/balance", status_code=403, json={"error": {"code": 403, "message": "stale"}})
        rec.add("POST", "/v2/oauth/connectid/refresh-token/android",
                json={"id": AUTH_ID, "access_token": "TOKEN-B", "refresh_token": "REFRESH-B",
                      "expire_at": int(time.time()) + 7200, "msisdn": MSISDN_880})
        rec.add("GET", "/balance", json={"balance": 5})  # served to the post-refresh retry

        data = client.get_json("GET", "/balance", auth_mode=AuthMode.SUBSCRIBER)
        assert data == {"balance": 5}
        assert state.auth.access_token == "TOKEN-B"
        assert len(rec.requests) == 3  # original + refresh + retry

    def test_refresh_rate_guard(self, make_client, state):
        state.auth.created_at = int(time.time())  # fresh token
        client, rec = make_client()
        rec.add("GET", "/balance", status_code=403, json={})
        response = client.request("GET", "/balance", auth_mode=AuthMode.SUBSCRIBER)
        assert response.status_code == 403
        assert len(rec.requests) == 1  # no refresh attempt, no retry

    def test_proactive_refresh_when_expiring(self, make_client, state):
        state.auth.expire_at = int(time.time()) + 100  # inside the 600s skew
        state.auth.created_at = int(time.time()) - 1200  # old enough to refresh
        client, rec = make_client()
        rec.add("POST", "/v2/oauth/connectid/refresh-token/android",
                json={"access_token": "TOKEN-B", "refresh_token": "REFRESH-B",
                      "expire_at": int(time.time()) + 7200})
        rec.add("GET", "/balance", json={"balance": 1})
        client.get_json("GET", "/balance", auth_mode=AuthMode.SUBSCRIBER)
        assert state.auth.access_token == "TOKEN-B"
        assert len(rec.requests) == 2
