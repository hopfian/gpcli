"""Balance transfer — registration, transfer, PIN management.

Wire formats from `ApiInterface.java`, `ResetPinPostApiService.java` and the
`BalanceTransferViewModel`/`BalanceTransferChangePinActivity` smali (jadx
failed to decompile the transfer body — recovered from smali):

* ``GET  balance/register``                                    — register
* ``POST balance/transfer  {payee, amount, pin}``              — transfer
* ``POST balance/pin       {old_pin, new_pin, confirm_pin}``   — change PIN
* ``POST /mygpapi/balance-transfer/reset-pin/initiate``        — OTP dispatch
* ``POST /mygpapi/balance-transfer/reset-pin/otp-verify``
       ``{reference_id, otp, msisdn}``
* ``POST /mygpapi/balance-transfer/reset-pin {new_pin, confirm_pin}``

Live-verified 2026-08-30: transfer requests reach GP's core billing system
(error SMS with reference numbers arrives, e.g. ``4596: insufficient credit``);
registration on an already-enrolled account returns the ``401 Unsuccessful``
envelope while the SMS carries "You have already activated P2P_SERVICE".
The API response itself only carries the bare envelope — detailed failure
reasons are SMS-delivered.
"""

from __future__ import annotations

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import BalanceTransferResponse

REGISTER_ENDPOINT = "/balance/register"
TRANSFER_ENDPOINT = "/balance/transfer"
CHANGE_PIN_ENDPOINT = "/balance/pin"
RESET_PIN_INITIATE_ENDPOINT = "/balance-transfer/reset-pin/initiate"
RESET_PIN_VERIFY_ENDPOINT = "/balance-transfer/reset-pin/otp-verify"
RESET_PIN_ENDPOINT = "/balance-transfer/reset-pin"


class TransferService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def register(self) -> BalanceTransferResponse:
        """`GET balance/register` — enroll the account for balance transfer."""
        data = self.client.get_json("GET", REGISTER_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return BalanceTransferResponse.model_validate(data)

    def send(self, payee: str, amount: str, pin: str) -> BalanceTransferResponse:
        """`POST balance/transfer` — move balance to another subscriber."""
        data = self.client.get_json(
            "POST", TRANSFER_ENDPOINT,
            json_body={"payee": payee, "amount": amount, "pin": pin},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return BalanceTransferResponse.model_validate(data)

    def change_pin(self, old_pin: str, new_pin: str, confirm_pin: str) -> BalanceTransferResponse:
        """`POST balance/pin` — change the transfer PIN (requires the old one)."""
        data = self.client.get_json(
            "POST", CHANGE_PIN_ENDPOINT,
            json_body={"old_pin": old_pin, "new_pin": new_pin, "confirm_pin": confirm_pin},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return BalanceTransferResponse.model_validate(data)

    def reset_pin_initiate(self) -> dict:
        """`POST reset-pin/initiate` — dispatches an OTP, returns reference_id."""
        data = self.client.get_json(
            "POST", RESET_PIN_INITIATE_ENDPOINT, json_body={}, auth_mode=AuthMode.SUBSCRIBER
        )
        return data

    def reset_pin_verify(self, reference_id: str, otp: str, msisdn: str) -> dict:
        """`POST reset-pin/otp-verify` — verify the OTP for a reset flow."""
        return self.client.get_json(
            "POST", RESET_PIN_VERIFY_ENDPOINT,
            json_body={"reference_id": reference_id, "otp": otp, "msisdn": msisdn},
            auth_mode=AuthMode.SUBSCRIBER,
        )

    def reset_pin_set(self, new_pin: str, confirm_pin: str) -> dict:
        """`POST reset-pin` — set the new PIN (after a verified OTP)."""
        return self.client.get_json(
            "POST", RESET_PIN_ENDPOINT,
            json_body={"new_pin": new_pin, "confirm_pin": confirm_pin},
            auth_mode=AuthMode.SUBSCRIBER,
        )
