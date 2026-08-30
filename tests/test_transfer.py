"""Balance transfer service — wire bodies and response handling."""

import json

from constants import MSISDN_880

from gpcli.models import BalanceTransferResponse
from gpcli.services.transfer import (
    CHANGE_PIN_ENDPOINT,
    REGISTER_ENDPOINT,
    RESET_PIN_ENDPOINT,
    RESET_PIN_INITIATE_ENDPOINT,
    RESET_PIN_VERIFY_ENDPOINT,
    TRANSFER_ENDPOINT,
    TransferService,
)


def test_transfer_body(make_client):
    client, rec = make_client()
    rec.add("POST", TRANSFER_ENDPOINT, json={"result": "success", "message": "Transfer done"})
    response = TransferService(client).send("01712345678", "50", "1234")
    body = json.loads(rec.requests[0].content)
    assert body == {"payee": "01712345678", "amount": "50", "pin": "1234"}
    assert response.ok


def test_register_is_get(make_client):
    client, rec = make_client()
    rec.add("GET", REGISTER_ENDPOINT, json={"status": 200, "result": "success", "message": "registered"})
    response = TransferService(client).register()
    assert rec.requests[0].method == "GET"
    assert response.ok


def test_change_pin_body(make_client):
    client, rec = make_client()
    rec.add("POST", CHANGE_PIN_ENDPOINT, json={"result": "failed", "message": "wrong pin"})
    response = TransferService(client).change_pin("0000", "1111", "1111")
    body = json.loads(rec.requests[0].content)
    assert body == {"old_pin": "0000", "new_pin": "1111", "confirm_pin": "1111"}
    assert not response.ok


def test_reset_pin_chain(make_client):
    client, rec = make_client()
    rec.add("POST", RESET_PIN_INITIATE_ENDPOINT,
            json={"data": {"otp_type": "sms", "reference_id": "REF-123"}})
    rec.add("POST", RESET_PIN_VERIFY_ENDPOINT,
            json={"data": {"is_otp_verified": True}})
    rec.add("POST", RESET_PIN_ENDPOINT, json={"result": "success", "message": "PIN set"})

    service = TransferService(client)
    initiate = service.reset_pin_initiate()
    assert initiate["data"]["reference_id"] == "REF-123"

    verify = service.reset_pin_verify("REF-123", "999111", MSISDN_880)
    body = json.loads(rec.requests[1].content)
    assert body == {"reference_id": "REF-123", "otp": "999111", "msisdn": MSISDN_880}
    assert verify["data"]["is_otp_verified"] is True

    service.reset_pin_set("2222", "2222")
    body = json.loads(rec.requests[2].content)
    assert body == {"new_pin": "2222", "confirm_pin": "2222"}


def test_transfer_uses_subscriber_auth(make_client):
    client, rec = make_client()
    rec.add("POST", TRANSFER_ENDPOINT, json={"result": "success"})
    TransferService(client).send("017", "1", "1")
    assert rec.requests[0].headers["Authorization"] == "Bearer TOKEN-A"


def test_balance_transfer_response_envelope():
    ok = BalanceTransferResponse.model_validate({"status": 200, "result": "Success", "message": "done"})
    assert ok.ok
    bad = BalanceTransferResponse.model_validate({"status": 400, "result": "failed", "message": "nope"})
    assert not bad.ok
    assert not BalanceTransferResponse.model_validate({}).ok
