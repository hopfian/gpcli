"""AutoPay — scheduled and low-balance automatic recharges.

Wire contract (from `AutoPayApiInterface`, setup/update smali and the
BaseResponse envelope; recovered from the decompiled sources):

* ``GET  v1/auto-payment/subscription-list?connection_type=prepaid``
  -> BaseResponse ``{code, status, message, data: {setting, subscription}}``
* ``POST v1/auto-payment/pay`` — create::

      {amount, conn_type: "prepaid", frequency, frequency_unit,
       product_code, product_type: "low_balance"|"scheduled_recharge",
       provisioning_msisdn (local 01…), service_provider,
       service_provider_identifier, start_from (yyyy-MM-dd, default tomorrow)}

  For low-balance: frequency = "" (empty string);
  product_code/frequency_unit come from ``settings.products[]``.
* ``PUT  v1/auto-payment/{id}/update`` — same minus conn_type/product_code
* ``DELETE v1/auto-payment/{id}/cancel?provisioning_msisdn=<local 01…>``
* ``GET  v1/auto-payment/recent-recharge-numbers-list``
* ``POST v1/msisdn-validator/validate`` — {msisdn (880 13-digit), eb_due_check,
  connection_type_check} -> MsisdnStatus
* ``GET  v2/payment-methods`` — saved payment methods (source of
  service_provider / service_provider_identifier values)
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import AutoPayListResponse, AutoPayProduct
from gpcli.msisdn import local_msisdn

__all__ = ["AutoPayService", "local_msisdn"]

SUBSCRIPTION_LIST_ENDPOINT = "/v1/auto-payment/subscription-list"
PAY_ENDPOINT = "/v1/auto-payment/pay"
UPDATE_ENDPOINT = "/v1/auto-payment/{id}/update"
CANCEL_ENDPOINT = "/v1/auto-payment/{id}/cancel"
RECENT_NUMBERS_ENDPOINT = "/v1/auto-payment/recent-recharge-numbers-list"
VALIDATE_MSISDN_ENDPOINT = "/v1/msisdn-validator/validate"
PAYMENT_METHODS_ENDPOINT = "/v2/payment-methods"

PRODUCT_TYPE_LOW_BALANCE = "low_balance"
PRODUCT_TYPE_SCHEDULED = "scheduled_recharge"


def _unwrap(data: dict) -> Any:
    """BaseResponse envelope: {code, status, message, data}."""
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


class AutoPayService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def list(self, connection_type: str = "prepaid") -> AutoPayListResponse:
        data = self.client.get_json(
            "GET", SUBSCRIPTION_LIST_ENDPOINT,
            params={"connection_type": connection_type},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return AutoPayListResponse.model_validate(_unwrap(data) or {})

    def products(self, connection_type: str = "prepaid") -> list[AutoPayProduct]:
        return self.list(connection_type).products

    def product(self, product_type: str, connection_type: str = "prepaid") -> AutoPayProduct | None:
        for product in self.products(connection_type):
            if product.product_type == product_type:
                return product
        return None

    def recent_numbers(self) -> list[str]:
        data = self.client.get_json("GET", RECENT_NUMBERS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        unwrapped = _unwrap(data)
        if isinstance(unwrapped, list):
            return [str(item) for item in unwrapped]
        return []

    def validate_msisdn(
        self, msisdn_880: str, *, eb_due_check: bool = True,
        connection_type_check: bool = True, operator_check: bool = True,
    ) -> dict:
        return self.client.get_json(
            "POST", VALIDATE_MSISDN_ENDPOINT,
            json_body={
                "msisdn": msisdn_880,
                "eb_due_check": eb_due_check,
                "connection_type_check": connection_type_check,
                "operator_check": operator_check,
            },
            auth_mode=AuthMode.SUBSCRIBER,
        )

    def payment_methods(self) -> list[dict]:
        data = self.client.get_json("GET", PAYMENT_METHODS_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        unwrapped = _unwrap(data)
        if isinstance(unwrapped, list):
            return [item for item in unwrapped if isinstance(item, dict)]
        if isinstance(unwrapped, dict):
            # some envelopes nest one level deeper (e.g. {"payment_methods": [...]})
            for value in unwrapped.values():
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    def setup(
        self,
        *,
        amount: str,
        provisioning_msisdn: str,
        service_provider: str,
        service_provider_identifier: str,
        frequency: str | None = None,
        start_from: date | None = None,
        connection_type: str = "prepaid",
    ) -> dict:
        """Create a subscription. `frequency=None` -> low-balance; a value -> scheduled."""
        product_type = PRODUCT_TYPE_SCHEDULED if frequency is not None else PRODUCT_TYPE_LOW_BALANCE
        product = self.product(product_type, connection_type)
        if product is None:
            from gpcli.errors import MyGPError

            raise MyGPError(
                f"no {product_type!r} product configured for autopay — run `gpcli autopay products`"
            )
        body = {
            "amount": amount,
            "conn_type": connection_type,
            "frequency": frequency if frequency is not None else "",
            "frequency_unit": product.frequency_unit or "",
            "product_code": product.product_code,
            "product_type": product.product_type,
            "provisioning_msisdn": local_msisdn(provisioning_msisdn),
            "service_provider": service_provider,
            "service_provider_identifier": service_provider_identifier,
            "start_from": (start_from or date.today() + timedelta(days=1)).isoformat(),
        }
        return self.client.get_json("POST", PAY_ENDPOINT, json_body=body, auth_mode=AuthMode.SUBSCRIBER)

    def update(
        self,
        subscription_id: int,
        *,
        amount: str,
        provisioning_msisdn: str,
        service_provider: str,
        service_provider_identifier: str,
        frequency: str | None = None,
        start_from: date | None = None,
        connection_type: str = "prepaid",
    ) -> dict:
        product_type = PRODUCT_TYPE_SCHEDULED if frequency is not None else PRODUCT_TYPE_LOW_BALANCE
        product = self.product(product_type, connection_type)
        body = {
            "provisioning_msisdn": local_msisdn(provisioning_msisdn),
            "amount": amount,
            "product_type": product.product_type if product else product_type,
            "frequency": frequency if frequency is not None else "",
            "frequency_unit": product.frequency_unit if product else None,
            "service_provider": service_provider,
            "service_provider_identifier": service_provider_identifier,
            "start_from": (start_from or date.today() + timedelta(days=1)).isoformat(),
        }
        return self.client.get_json(
            "PUT", UPDATE_ENDPOINT.format(id=subscription_id),
            json_body=body, auth_mode=AuthMode.SUBSCRIBER,
        )

    def cancel(self, subscription_id: int, provisioning_msisdn: str) -> dict:
        return self.client.get_json(
            "DELETE", CANCEL_ENDPOINT.format(id=subscription_id),
            params={"provisioning_msisdn": local_msisdn(provisioning_msisdn)},
            auth_mode=AuthMode.SUBSCRIBER,
        )
