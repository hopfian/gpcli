"""SIM, FnF, comms, offers and partner services — wire formats."""

import json

from constants import MSISDN_880

from gpcli.models import (
    BiometricSimList,
    FnfList,
    GAOfferInfo,
    PackItem,
    SimOwnershipCertificate,
    WelcomeTune,
)
from gpcli.services.fnf import FnfService
from gpcli.services.mca import McaService
from gpcli.services.netcare import NetworkComplainService
from gpcli.services.offers import campaign_activate_body
from gpcli.services.partners import PartnerService
from gpcli.services.sim import SimService
from gpcli.services.welcome_tune import WelcomeTuneService


class TestSimService:
    def test_certificate(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/v1/ownership-certificate",
                json={"status": "success", "data": "<html>CERT</html>"})
        cert = SimService(client).certificate()
        assert cert.ok
        assert cert.data == "<html>CERT</html>"

    def test_biometric_sim_list_form_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/v2/customers/biometric-msisdn",
                json={"data": {"active_sim_list": [{"msisdn": "8801...", "operator": "GP"}]}})
        result = SimService(client).sim_list("1234")
        # form-encoded, snake_case field
        assert "last_four_digit_id=1234" in rec.requests[0].content.decode()
        assert len(result.active_sims) == 1
        assert result.active_sims[0].operator == "GP"

    def test_sim_list_model(self):
        data = BiometricSimList.model_validate({
            "data": {
                "active_sim_list": [{"msisdn": "1", "operator": "GP", "status": "active"}],
                "bondho_sim_list": [{"msisdn": "2", "operator": "GP", "status": "bondho"}],
                "other_operator_sim_list": [{"msisdn": "3", "operator": "Robi"}],
            }
        })
        assert len(data.active_sims) == 1
        assert data.bondho_sims[0].status == "bondho"
        assert data.other_operator_sims[0].operator == "Robi"


class TestFnfService:
    def test_add_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/fnf-add", json={"status": "success", "remarks": "ok"})
        FnfService(client).add("01712345678", super_fnf=True)
        body = json.loads(rec.requests[0].content)
        assert body == {"fnf": "01712345678", "is_super": "1"}

    def test_delete_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/fnf-delete", json={"status": "success"})
        FnfService(client).remove("01712345678")
        body = json.loads(rec.requests[0].content)
        assert body == {"fnf": "01712345678", "is_super": "0"}

    def test_list_model(self):
        data = FnfList.model_validate({
            "normal_fnf": [{"fnf": "0171", "requestdate": "2026-01-01", "changedate": "2026-01-02"}],
            "super_fnf": [],
            "info": {"totalnormalFnF": 5, "totalsuperFnF": 3, "usednormalFnF": 1, "usedsuperFnF": 0},
        })
        assert data.info.total == 8
        assert data.info.used_total == 1
        assert data.normal_fnf[0].fnf == "0171"


class TestMcaService:
    def test_set_body_is_boolean(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/mca", json={"status": "pending"})
        McaService(client).set(True)
        assert json.loads(rec.requests[0].content) == {"status": True}

    def test_status(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/mca", json={"status": "1", "due_date": "2026-09-30"})
        result = McaService(client).status()
        assert result["status"] == "1"


class TestWelcomeTuneService:
    def test_pascal_case_model(self):
        tune = WelcomeTune.model_validate({
            "Price": 15.0, "SingerName": "Artist", "ToneCode": "T123",
            "ToneName": "Song", "ToneValidDay": 30,
        })
        assert tune.ToneCode == "T123"
        assert tune.Price == 15.0

    def test_search_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/wt/search", json={"tuneList": []})
        WelcomeTuneService(client).search("hello")
        assert json.loads(rec.requests[0].content) == {"keyword": "hello"}

    def test_activate_v2_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/v2/wt/activate", json={"result": "success"})
        WelcomeTuneService(client).activate("T123")
        body = json.loads(rec.requests[0].content)
        assert body["characteristic"] == [{"name": "tone_code", "value": "T123"}]
        assert "reference_id" in body


class TestNetworkComplainService:
    def test_submit_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/common/v1/network-complain-feedbacks", json={"status": "success"})
        NetworkComplainService(client).submit(
            [{"id": 1, "type": "textarea", "feedback": "poor signal"}],
            meta={"lat": 23.8, "long": 90.4},
        )
        body = json.loads(rec.requests[0].content)
        assert body["questions"] == [{"id": 1, "type": "textarea", "feedback": "poor signal"}]
        assert body["meta"] == {"lat": 23.8, "long": 90.4}


class TestOffersService:
    def test_campaign_activate_body(self):
        pack = PackItem.model_validate({
            "id": "123", "keyword": "PAYGO_ON", "price": "0", "type": "internet",
            "attributes": ["pay_go_on"],
        })
        body = campaign_activate_body(pack, MSISDN_880)
        assert body["campaign_id"] == "PAYGO_ON"
        assert body["catalog_id"] == "123"
        assert body["msisdn"] == MSISDN_880
        assert body["is_crm"] == "1"
        assert body["eb"] == "0"

    def test_auto_renew_camel_case_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/internet-renew", json={"status": "pending"})
        from gpcli.services.offers import OffersService

        OffersService(client).set_auto_renew("SC123", True)
        body = json.loads(rec.requests[0].content)
        # camelCase literal from PackRenewRequest.java
        assert body == {"status": 1, "productShortCode": "SC123"}

    def test_vas_stop_all_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/services/v1/vas/set-status", json={"status": "success"})
        from gpcli.services.offers import OffersService

        OffersService(client).vas_stop_all([
            {"service_id": "S1", "partner": "p1", "type": "vas"},
            {"service_id": "S2", "partner": "p2", "type": "vas"},
        ])
        body = json.loads(rec.requests[0].content)
        assert body["action"] == "deactive_all"
        assert body["partners"] == ["p1", "p2"]
        assert body["serviceIds"] == ["S1", "S2"]

    def test_ga_offer_model(self):
        info = GAOfferInfo.model_validate(
            {"is_current_month_availed": 0, "remaining": 3, "total_campaign_period": 30}
        )
        assert info.remaining == 3


class TestPartnerService:
    def test_chatbot_token_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/services/v1/partners/chatbot/get-token",
                json={"token": "T", "token_info": {"exp": 999}})
        result = PartnerService(client).chatbot_token()
        body = json.loads(rec.requests[0].content)
        assert set(body) == {"consent", "device_id"}
        assert body["consent"] is True
        assert result.token == "T"

    def test_drm_token_body(self, make_client):
        client, rec = make_client()
        rec.add("POST", "/services/v1/drm/lionsgate/get-token",
                json={"data": {"token": "DRM-TOKEN"}})
        token = PartnerService(client).drm_token("lionsgate", "PID-1")
        assert token == "DRM-TOKEN"
        assert json.loads(rec.requests[0].content) == {"pid": "PID-1", "scheme": "widevine"}

    def test_chat_url(self):
        assert PartnerService.chat_url("XYZ").endswith("srt/chatbot?token=XYZ")


def test_certificate_model_limit():
    cert = SimOwnershipCertificate.model_validate({"status": "failed"})
    assert not cert.ok
