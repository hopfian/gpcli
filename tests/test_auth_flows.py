"""Auth service flows — OTP staging/verification, silent login, guest minting, logout.

These pin the wire contracts the changelog claims are "frozen": the OTP body
shape, the staging handoff, the IP-gating error semantics, the guest OAuth
form post, and logout's endpoint choice.
"""

from __future__ import annotations

import json
import time
from urllib.parse import parse_qs

import pytest

from gpcli.errors import ApiError, AuthRequiredError, GuestFlowError, SilentLoginUnavailable
from gpcli.models import Auth, GuestSession
from gpcli.services.auth import AuthService
from tests.constants import AUTH_ID, MSISDN_880


def _token_success() -> dict:
    return {
        "id": AUTH_ID,
        "access_token": "sub-token",
        "token": "sub-token",
        "refresh_token": "refresh",
        "msisdn": MSISDN_880,
        "expire_at": int(time.time()) + 86400,
    }


class TestOtpFlow:
    def test_send_otp_normalizes_and_stages(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/v2/otp-login", json={"result": "success"})
        AuthService(client).send_otp("01320548227")  # national form in
        assert rec.requests[0].url.params["msisdn"] == "8801320548227"
        assert client.state.staged_msisdn == "8801320548227"

    def test_send_otp_failure_leaves_no_stage(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/v2/otp-login", json={"result": "failed"})
        AuthService(client).send_otp("8801700000000")
        assert client.state.staged_msisdn is None

    def test_verify_otp_body_shape(self, make_client, state):
        client, rec = make_client()
        rec.add("POST", "/v2/otp-login", json=_token_success())
        AuthService(client).verify_otp(" 1234 ", msisdn="01712345678")
        body = json.loads(rec.requests[-1].content)
        assert body["msisdn"] == "8801712345678"  # national accepted, normalized out
        assert body["otp"] == "1234"  # stripped
        assert body["device_id"] == state.device.device_id
        assert body["device_model"] == state.device.device_model
        assert body["device_name"] == state.device.device_name
        assert body["app_version"]

    def test_verify_otp_falls_back_to_staged(self, make_client, state):
        client, rec = make_client()
        state.staged_msisdn = MSISDN_880
        rec.add("POST", "/v2/otp-login", json=_token_success())
        AuthService(client).verify_otp("999999")
        assert json.loads(rec.requests[-1].content)["msisdn"] == MSISDN_880

    def test_verify_otp_requires_a_number(self, make_client):
        client, _ = make_client()
        with pytest.raises(AuthRequiredError, match="send-otp"):
            AuthService(client).verify_otp("1234")

    def test_verify_otp_persists_and_consumes_the_stage(self, make_client, state):
        client, rec = make_client()
        state.staged_msisdn = MSISDN_880
        rec.add("POST", "/v2/otp-login", json=_token_success())
        auth = AuthService(client).verify_otp("999999")
        assert auth.access_token == "sub-token"
        assert client.state.auth is not None and client.state.auth.access_token == "sub-token"
        assert client.state.staged_msisdn is None

    def test_verify_otp_rejects_empty_token(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/v2/otp-login", json={"id": 1})  # no access_token
        with pytest.raises(ApiError, match="no access token"):
            AuthService(client).verify_otp("1234", msisdn="8801700000000")


class TestNetworkMsisdn:
    def test_extracts_the_msisdn_key(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/msisdn", json={"msisdn": MSISDN_880})
        assert AuthService(client).network_msisdn() == MSISDN_880

    def test_falls_back_to_data_then_result_keys(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/msisdn", json={"data": "8801700000001"})
        assert AuthService(client).network_msisdn() == "8801700000001"

    def test_api_errors_mean_no_network_number(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/msisdn", status_code=500, text="edge error")
        assert AuthService(client).network_msisdn() is None


class TestSilentLogin:
    def test_ip_gate_403_is_silent_login_unavailable(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/code", status_code=403, text="nginx edge")
        with pytest.raises(SilentLoginUnavailable, match="mobile data"):
            AuthService(client).silent_login()

    def test_challenge_response_without_code_is_rejected(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/code", json={"status": "ok"})
        with pytest.raises(SilentLoginUnavailable, match="unexpected"):
            AuthService(client).silent_login()

    def test_challenge_is_answered_and_session_persisted(self, make_client, state):
        client, rec = make_client()
        rec.add("GET", "/code", json={"code": "server-challenge"})
        rec.add("POST", "/v2/code", json=_token_success())
        auth = AuthService(client).silent_login()
        assert auth.access_token == "sub-token"
        assert client.state.auth is not None
        # the answer body is the AES-CTR silent-login envelope (pinned in test_crypto)
        answered = json.loads(rec.requests[-1].content)
        assert isinstance(answered, dict) and answered


class TestGuestLogin:
    def test_mints_identity_then_oauth_token(self, make_client, state):
        client, rec = make_client()
        rec.add("POST", "/guest-login",
                json={"userId": "u1", "clientId": "c1", "clientSecret": "s1"})
        rec.add("POST", "oauth/v2/token",
                json={"status": "APPROVED", "accessToken": "gt", "expiresIn": "3600"})
        guest = AuthService(client).guest_login()
        assert guest.user_id == "u1"
        assert guest.access_token == "gt"
        assert guest.expires_at == guest.issued_at + 3600

    def test_guest_login_carries_advertising_id(self, make_client, state):
        # the server rejects a null aaId (402) — the app sends a UUID
        client, rec = make_client()
        rec.add("POST", "/guest-login",
                json={"userId": "u1", "clientId": "c1", "clientSecret": "s1"})
        rec.add("POST", "oauth/v2/token",
                json={"status": "APPROVED", "accessToken": "gt", "expiresIn": "3600"})
        AuthService(client).guest_login()
        body = json.loads(rec.requests[0].content)
        assert body["deviceId"] == state.device.device_id
        assert body["aaId"]

    def test_oauth_call_is_a_raw_form_post(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/guest-login",
                json={"userId": "u1", "clientId": "c1", "clientSecret": "s1"})
        rec.add("POST", "oauth/v2/token",
                json={"status": "APPROVED", "accessToken": "gt", "expiresIn": "3600"})
        AuthService(client).guest_login()
        form = parse_qs(rec.requests[-1].content.decode())
        assert form["client_id"] == ["c1"]
        assert form["client_secret"] == ["s1"]
        assert form["grant_type"] == ["client_credentials"]
        assert form["userId"] == ["u1"]

    def test_refresh_token_reuses_the_identity(self, make_client, state):
        now = int(time.time())
        state.guest = GuestSession(
            user_id="u", client_id="c", client_secret="s",
            access_token="old", issued_at=now - 100, expires_at=now + 3000,
        )
        client, rec = make_client()
        rec.add("POST", "oauth/v2/token",
                json={"status": "APPROVED", "accessToken": "new", "expiresIn": "3600"})
        guest = AuthService(client).guest_login(refresh_token=True)
        assert guest.access_token == "new"
        assert len(rec.requests) == 1  # no /guest-login round-trip

    def test_expired_token_re_mints_without_being_asked(self, make_client, state):
        now = int(time.time())
        state.guest = GuestSession(
            user_id="u", client_id="c", client_secret="s",
            access_token="old", issued_at=now - 7200, expires_at=now - 60,
        )
        client, rec = make_client()
        rec.add("POST", "oauth/v2/token",
                json={"status": "APPROVED", "accessToken": "new", "expiresIn": "3600"})
        guest = AuthService(client).guest_login()
        assert guest.access_token == "new"

    def test_guest_login_without_user_id_fails_cleanly(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/guest-login", json={"userId": "", "clientId": "c", "clientSecret": "s"})
        with pytest.raises(GuestFlowError, match="userId"):
            AuthService(client).guest_login()

    def test_oauth_error_envelope_raises_guest_flow_error(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/guest-login",
                json={"userId": "u1", "clientId": "c1", "clientSecret": "s1"})
        rec.add("POST", "oauth/v2/token",
                json={"error": {"code": "402", "message": "failed"}})
        with pytest.raises(GuestFlowError, match="402"):
            AuthService(client).guest_login()


class TestLogout:
    def test_logout_hits_the_endpoint_and_clears_state(self, make_client, state):
        client, rec = make_client()
        state.auth = Auth(id=AUTH_ID, access_token="t", msisdn=MSISDN_880,
                          expire_at=int(time.time()) + 3600)
        rec.add("GET", "/logout", json={"status": "success"})
        AuthService(client).logout()
        assert client.state.auth is None
        assert "logout" in str(rec.requests[-1].url)

    def test_logout_all_uses_the_all_devices_endpoint(self, make_client, state):
        client, rec = make_client()
        state.auth = Auth(id=AUTH_ID, access_token="t", msisdn=MSISDN_880,
                          expire_at=int(time.time()) + 3600)
        rec.add("GET", "logout-from-all-device", json={"status": "success"})
        AuthService(client).logout(all_devices=True)
        assert "logout-from-all-device" in str(rec.requests[-1].url)
        assert client.state.auth is None

    def test_logout_clears_local_state_even_when_the_api_fails(self, make_client, state):
        client, rec = make_client()
        state.auth = Auth(id=AUTH_ID, access_token="t", msisdn=MSISDN_880,
                          expire_at=int(time.time()) + 3600)
        rec.add("GET", "/logout", status_code=500, text="edge error")
        AuthService(client).logout()
        assert client.state.auth is None

    def test_logout_without_a_session_is_a_local_clear(self, make_client, state):
        client, rec = make_client()
        state.auth = None  # the fixture defaults to a live session
        AuthService(client).logout()
        assert client.state.auth is None
        assert rec.requests == []  # nothing to invalidate server-side
