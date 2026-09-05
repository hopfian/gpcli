"""Purchase & recharge — body builders and service wiring."""

import json

from constants import MSISDN_880, MSISDN_LOCAL

from gpcli.bodies import build_pack_data, build_recharge_data
from gpcli.models import PackItem
from gpcli.services.purchase import PurchaseService


def _pack(**overrides) -> PackItem:
    base = {
        "id": "4575", "type": "internet", "title": "1 GB Booster",
        "keyword": "1GB_1D", "price": "19",
        "attributes": ["eb_eligible_offer"],
    }
    base.update(overrides)
    return PackItem.model_validate(base)


class TestBuildRechargeData:
    def test_make_payment_body_shape(self):
        body = build_recharge_data(
            amount=50, msisdn=MSISDN_880, provider="bkash",
            identifier="IDX", main_balance="12.5", eb_due=34.95,
        )
        assert body["amount"] == "50"
        assert body["recharge_msisdn"] == MSISDN_LOCAL  # local format
        assert body["service_provider"] == "bkash"
        assert body["identifier"] == "IDX"
        assert body["main_balance"] == "12.5"
        assert body["eb_due"] == 34.95
        assert body["connection_type"] == "prepaid"
        assert body["is_new_user"] == 0

    def test_pack_fields_copied_when_present(self):
        pack = _pack(recharge_journey={"sub_channel": "recharge_and_activate_vanilla"})
        body = build_recharge_data(
            amount=19, msisdn=MSISDN_880, provider="", identifier="",
            main_balance="0", eb_due=0, pack=pack,
        )
        assert body["pack_name"] == "1 GB Booster"
        assert body["crm_keyword"] == "1GB_1D"
        assert body["catalog_id"] == "4575"
        assert body["channel"] == "recharge_and_activate_vanilla"


class TestBuildPackData:
    def test_api_l_body_plus_additions(self):
        pack = _pack()
        body = build_pack_data(pack, MSISDN_880, otp="1234", recharge=19)
        assert body["campaign_id"] == "1GB_1D"
        assert body["catalog_id"] == "4575"
        assert body["msisdn"] == MSISDN_880
        assert body["is_crm"] == "1"
        assert body["eb"] == "1"  # eb_eligible_offer attribute
        assert body["forced"] == "1"
        assert body["otp"] == "1234"
        assert body["content_source"] == "recharge_and_activate"
        assert body["recharge"] == "19"

    def test_no_otp_key_when_empty(self):
        body = build_pack_data(_pack(), MSISDN_880)
        assert "otp" not in body


class TestPurchaseServiceWiring:
    def test_recharge_gateway_body(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"balance": 5, "service_class": 456,
                                         "emergency_balance": {"due": 34.95, "data_loan": 0}})
        rec.add("POST", "/recharge", json={"payment_url": "https://pay.example/x"})
        result = PurchaseService(client).recharge_gateway(50)
        body = json.loads(rec.requests[-1].content)
        assert body["amount"] == 50
        assert body["platform"] == "android"
        assert body["type"] == "PREPAID"
        assert body["mobile"] == MSISDN_LOCAL
        assert body["email"] == f"{MSISDN_880}@grameenphone.com"
        assert body["eb_due"] == 35  # ceil(34.95)
        assert result.payment_url == "https://pay.example/x"

    def test_wallet_payment_body(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"balance": 0, "emergency_balance": {}})
        rec.add("POST", "/payment-gateway/payment",
                json={"code": 200, "status": "success", "data": {"remarks": "done"}})
        result = PurchaseService(client).pay(
            "50", provider="bkash", identifier="IDX"
        )
        body = json.loads(rec.requests[-1].content)
        assert body["amount"] == "50"
        assert body["service_provider"] == "bkash"
        assert body["identifier"] == "IDX"
        assert body["recharge_msisdn"] == MSISDN_LOCAL
        assert result.ok is True

    def test_purchase_pack_body(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"balance": 0, "service_class": 456,
                                         "emergency_balance": {}})
        rec.add("POST", "/recharge-and-activate",
                json={"data": {"status": "success", "direct_recharge": {"rechargeAmount": 19}}})
        pack = _pack()
        response = PurchaseService(client).purchase_pack(pack, provider="bkash", identifier="IDX")
        body = json.loads(rec.requests[-1].content)
        assert body["recharge_type"] == "direct_recharge"
        assert body["pack_type"] == "campaign"
        assert body["journey_type"] == "recharge_and_activate"
        assert body["recharge_data"]["amount"] == "19"
        assert body["pack_data"]["campaign_id"] == "1GB_1D"
        assert body["pack_data"]["forced"] == "1"
        # service class header present
        assert rec.requests[-1].headers["X-Service-Class-A"] == "456"
        assert response.ok

    def test_purchase_pack_action_required(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"balance": 0, "emergency_balance": {}})
        rec.add("POST", "/recharge-and-activate",
                json={"data": {"status": "action_required",
                               "url": {"payment_url": "https://pay.example/complete"}}})
        pack = _pack()
        response = PurchaseService(client).purchase_pack(pack)
        assert response.action_required
        assert response.data.payment_url == "https://pay.example/complete"

    def test_find_pack(self, make_client):
        client, rec = make_client()
        catalog = {"catalogs": [
            {"id": "4575", "keyword": "1GB_1D", "title": "1 GB Booster",
             "type": "internet", "price": "19"}
        ]}
        rec.add("GET", "/v3/catalogs", json=catalog)  # one-shot routes: one per find
        rec.add("GET", "/v3/catalogs", json=catalog)
        rec.add("GET", "/v3/catalogs", json=catalog)
        service = PurchaseService(client)
        assert service.find_pack("4575").title == "1 GB Booster"
        assert service.find_pack("1GB_1D").id == "4575"
        assert service.find_pack("nonexistent") is None

    def test_bound_methods_and_resolution(self, make_client):
        client, rec = make_client()
        balance = {
            "balance": 100,
            "connected_payment_methods": [
                {"type": "bkash", "wallet_no": "013#####227", "bind_status": 1,
                 "is_preferred": False, "identifier": "TkVBUEFTSA=="},
                {"type": "nagad", "wallet_no": "017#####798", "bind_status": 1,
                 "is_preferred": True, "identifier": "TkFHSUQ="},
                {"type": "card", "wallet_no": "", "bind_status": 0,
                 "identifier": "Tk9QRQ=="},
            ],
        }
        for _ in range(5):  # one-shot routes: 1 list + 4 resolves
            rec.add("GET", "/balance", json=balance)
        service = PurchaseService(client)
        bound = service.bound_payment_methods()
        assert len(bound) == 3

        nagad = service.resolve_identifier("NAGAD")
        assert nagad is not None and nagad.identifier == "TkFHSUQ="
        assert nagad.is_preferred is True

        bkash = service.resolve_identifier("bkash")
        assert bkash is not None and bkash.wallet_no == "013#####227"

        assert service.resolve_identifier("card") is None  # bind_status 0 — not usable
        assert service.resolve_identifier("unknown") is None

    def test_pay_auto_resolves_identifier(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={
            "balance": 5,
            "connected_payment_methods": [
                {"type": "nagad", "wallet_no": "017#####798", "bind_status": 1,
                 "is_preferred": True, "identifier": "TkFHSUQ="},
            ],
        })
        rec.add("GET", "/balance", json={"balance": 5})  # pay()'s snapshot
        rec.add("POST", "/payment-gateway/payment",
                json={"code": 200, "status": "success", "data": {"remarks": "ok"}})
        service = PurchaseService(client)
        bound = service.resolve_identifier("nagad")
        result = service.pay("20", provider="nagad", identifier=bound.identifier)
        body = json.loads(rec.requests[-1].content)
        assert body["service_provider"] == "nagad"
        assert body["identifier"] == "TkFHSUQ="
        assert result.ok is True

    def test_pack_channel_derivation(self):
        assert PurchaseService._pack_channel(None) == ""
        pack = _pack(attributes=["recharge_journey_offer"])
        assert PurchaseService._pack_channel(pack) == "direct_recharge_offer"
        pack = _pack(keyword="FLXPLN_V2_L30_V300_D30G")
        assert PurchaseService._pack_channel(pack) == "recharge_and_activate_flexiplan"
        pack = _pack()
        assert PurchaseService._pack_channel(pack) == "recharge_and_activate_eb"


class TestResponseModels:
    def test_recharge_and_activate_response(self):
        from gpcli.models import RechargeAndActivateResponse

        ok = RechargeAndActivateResponse.model_validate({"data": {"status": "pending"}})
        assert ok.ok and not ok.action_required
        ar = RechargeAndActivateResponse.model_validate(
            {"data": {"status": "action_required", "url": {"payment_url": "https://x"}}}
        )
        assert ar.action_required and not ar.ok
        assert ar.data.payment_url == "https://x"

    def test_make_payment_result(self):
        from gpcli.models import MakePaymentResult

        assert MakePaymentResult(status="success").ok
        assert not MakePaymentResult(status="pending").ok  # wallet: success only
        assert not MakePaymentResult(status="failed").ok

    def test_direct_recharge_int_coercion(self):
        from gpcli.models import DirectRechargeData

        # the server sends dueAmount as an int despite the String schema
        data = DirectRechargeData.model_validate({
            "dueAmount": 0, "rechargeAmount": 20,
            "recharge_transaction_id": 12345, "serviceProvider": "NAGAD",
        })
        assert data.dueAmount == "0"
        assert data.recharge_transaction_id == "12345"
        assert data.rechargeAmount == 20  # int field stays int
        assert data.serviceProvider == "NAGAD"


class TestSessionMsisdn:
    def test_no_session_raises_auth_required(self, make_client, state):
        state.auth = None
        client, _ = make_client()
        import pytest

        from gpcli.errors import AuthRequiredError

        with pytest.raises(AuthRequiredError):
            PurchaseService(client).pay("20", provider="nagad", identifier="T")

    def test_explicit_msisdn_beats_session(self, make_client, state):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"balance": 1, "type": "prepaid"})
        rec.add("POST", "/payment-gateway/payment",
                json={"code": 200, "status": "success", "data": {}})
        PurchaseService(client).pay("20", provider="bkash",
                                     identifier="T", msisdn="01712345678")
        body = json.loads(rec.requests[-1].content)
        assert body["recharge_msisdn"] == "01712345678"

    def test_gateway_derives_postpaid_type(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"balance": 5, "type": "postpaid"})
        rec.add("POST", "/recharge", json={"payment_url": "https://pay.example/x"})
        PurchaseService(client).recharge_gateway(50)
        body = json.loads(rec.requests[-1].content)
        assert body["type"] == "POSTPAID"
        assert body["connection_type"] == "postpaid"


class TestBindFlow:
    def test_bind_headers_from_balance(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={
            "balance": 10,
            "internet_details": {"value": "1024.0", "unit": "MB"},
        })
        rec.add("POST", "/payment-gateway/bind/nagad",
                json={"status": "success", "data": {"url": "https://nagad.example/x"}})
        result = PurchaseService(client).bind_payment_method("nagad")
        request = rec.requests[-1]
        assert request.headers["REMAINING-OPEN-INTERNET"] == "1024"
        assert request.headers["wifi"] == "0"
        assert result.url == "https://nagad.example/x"

    def test_bind_headers_empty_without_details(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/balance", json={"balance": 10})
        rec.add("POST", "/payment-gateway/bind/bkash", json={"status": "success", "data": {}})
        PurchaseService(client).bind_payment_method("bkash")
        assert rec.requests[-1].headers["REMAINING-OPEN-INTERNET"] == ""

    def test_purchase_headers_carry_analytics_id(self, make_client):
        from gpcli.crypto import analytics_id

        client, rec = make_client()
        rec.add("GET", "/balance", json={"balance": 1, "service_class": 456})
        headers = PurchaseService(client)._purchase_headers()  # noqa: SLF001 — under test
        assert headers["X-Analytics-ID"] == analytics_id(MSISDN_880)
        assert headers["X-Service-Class-A"] == "456"
