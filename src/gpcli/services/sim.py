"""SIM & account services — ownership certificate, biometric SIM lists.

Wire formats (verified against the decompiled sources and the live API):

* ``GET  /v1/ownership-certificate``          -> {status, data: <certificate HTML>}
  (error code ``42901`` = daily download limit reached)
* ``GET  /v1/customers/get-id-document``      -> {data: {doc_type, msisdn}}
* ``POST /v2/customers/biometric-msisdn``    form: last_four_digit_id (snake_case)
  -> {data: {active_sim_list, bondho_sim_list, other_operator_sim_list, id_number}}
"""

from __future__ import annotations

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import BiometricDocType, BiometricSimList, SimOwnershipCertificate

OWNERSHIP_CERTIFICATE_ENDPOINT = "/v1/ownership-certificate"
DOC_TYPE_ENDPOINT = "/v1/customers/get-id-document"
BIOMETRIC_SIM_LIST_ENDPOINT = "/v2/customers/biometric-msisdn"


class SimService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def certificate(self) -> SimOwnershipCertificate:
        data = self.client.get_json("GET", OWNERSHIP_CERTIFICATE_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return SimOwnershipCertificate.model_validate(data)

    def doc_type(self) -> BiometricDocType:
        data = self.client.get_json("GET", DOC_TYPE_ENDPOINT, auth_mode=AuthMode.SUBSCRIBER)
        return BiometricDocType.model_validate(data)

    def sim_list(self, last_four_digit_id: str) -> BiometricSimList:
        data = self.client.get_json(
            "POST", BIOMETRIC_SIM_LIST_ENDPOINT,
            data={"last_four_digit_id": last_four_digit_id},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return BiometricSimList.model_validate(data)
