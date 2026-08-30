"""Partner services & support — token exchanges, DRM, Zee5, chat, support form.

Wire formats (verified against the decompiled sources and the live API):

* ``POST services/v1/partners/deen/get-token``  (no body)  -> PartnerServiceToken
* ``POST services/v1/partners/win/get-token``   (no body)  -> PartnerServiceToken
* ``POST services/v1/partners/chatbot/get-token`` {consent, device_id} -> PartnerToken
* ``POST services/v1/drm/{partner}/get-token``  {pid, scheme: "widevine"} -> {data: {token}}
* ``POST v2/zee5/tokens``  (empty body) -> {token}; ``GET v2/zee5/contents?hash=``
* Streaming content: ``GET v1/sbcontents/search`` / ``v1/sbcontents/partner?partner=…``
  (the AuthInterceptor skips the `id` param on exactly these paths)
* Support form: ``POST support {name, email, issue_type, message, device}``
* Live chat (current): chatbot partner token + ``https://mygp.grameenphone.com/mygpapi/srt/chatbot``
  loaded with ``Authorization: Bearer <token>`` and ``?token=`` appended.
"""

from __future__ import annotations

from gpcli.client import ApiCaller, AuthMode
from gpcli.models import PartnerServiceToken, PartnerToken

DEEN_TOKEN_ENDPOINT = "/services/v1/partners/deen/get-token"
WIN_TOKEN_ENDPOINT = "/services/v1/partners/win/get-token"
CHATBOT_TOKEN_ENDPOINT = "/services/v1/partners/chatbot/get-token"
DRM_TOKEN_ENDPOINT = "/services/v1/drm/{partner}/get-token"
ZEE5_TOKEN_ENDPOINT = "/v2/zee5/tokens"
ZEE5_CONTENTS_ENDPOINT = "/v2/zee5/contents"
SBCONTENTS_SEARCH_ENDPOINT = "/v1/sbcontents/search"
SBCONTENTS_PARTNER_ENDPOINT = "/v1/sbcontents/partner"
SUPPORT_ENDPOINT = "/support"

CHATBOT_CONTENT_URL = "https://mygp.grameenphone.com/mygpapi/srt/chatbot"


class PartnerService:
    def __init__(self, client: ApiCaller):
        self.client = client

    def deen_token(self) -> PartnerServiceToken:
        """Ibadah SDK token exchange (MyGP -> com.deenislamic.sdk)."""
        data = self.client.get_json(
            "POST", DEEN_TOKEN_ENDPOINT, json_body={}, auth_mode=AuthMode.SUBSCRIBER
        )
        return PartnerServiceToken.model_validate(data)

    def win_token(self) -> PartnerServiceToken:
        data = self.client.get_json(
            "POST", WIN_TOKEN_ENDPOINT, json_body={}, auth_mode=AuthMode.SUBSCRIBER
        )
        return PartnerServiceToken.model_validate(data)

    def chatbot_token(self, *, consent: bool = True) -> PartnerToken:
        """Live chat token — device_id is the app's advertising id."""
        device_id = self.client.state.device.device_id
        data = self.client.get_json(
            "POST", CHATBOT_TOKEN_ENDPOINT,
            json_body={"consent": consent, "device_id": device_id},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        return PartnerToken.model_validate(data)

    def drm_token(self, partner: str, pid: str) -> str:
        """Widevine DRM token for a streaming partner (lionsgate, chorki, …)."""
        data = self.client.get_json(
            "POST", DRM_TOKEN_ENDPOINT.format(partner=partner),
            json_body={"pid": pid, "scheme": "widevine"},
            auth_mode=AuthMode.SUBSCRIBER,
        )
        inner = data.get("data", {}) if isinstance(data, dict) else {}
        return str(inner.get("token", "")) if isinstance(inner, dict) else ""

    def zee5_token(self) -> str:
        data = self.client.get_json(
            "POST", ZEE5_TOKEN_ENDPOINT, json_body={}, auth_mode=AuthMode.SUBSCRIBER
        )
        return str(data.get("token", ""))

    def zee5_contents(self) -> dict:
        return self.client.get_json(
            "GET", ZEE5_CONTENTS_ENDPOINT, params={"hash": ""}, auth_mode=AuthMode.SUBSCRIBER
        )

    def sbcontents_search(
        self, partner: str, *, offset: int = 0, limit: int = 20,
        genre: str = "", next_page: str = "",
    ) -> dict:
        """Partner content browse (v1/sbcontents/search — partner-scoped)."""
        params: dict[str, str | int] = {"partner": partner, "offset": offset, "limit": limit}
        if genre:
            params["genre"] = genre
        if next_page:
            params["next_page"] = next_page
        return self.client.get_json(
            "GET", SBCONTENTS_SEARCH_ENDPOINT, params=params, auth_mode=AuthMode.SUBSCRIBER
        )

    def sbcontents_partner(self, partner: str, *, offset: int = 0, limit: int = 20) -> dict:
        return self.client.get_json(
            "GET", SBCONTENTS_PARTNER_ENDPOINT,
            params={"partner": partner, "offset": offset, "limit": limit},
            auth_mode=AuthMode.SUBSCRIBER,
        )

    def send_support(
        self, name: str, email: str, issue_type: str, message: str
    ) -> dict:
        """`POST /support` — the native email-support form."""
        device = {
            "os": "Android",
            "model": self.client.state.device.device_model,
            "manufacturer": self.client.state.device.device_name,
        }
        return self.client.get_json(
            "POST", SUPPORT_ENDPOINT,
            json_body={
                "name": name,
                "email": email,
                "issue_type": issue_type,
                "message": message,
                "device": device,
            },
            auth_mode=AuthMode.SUBSCRIBER,
        )

    @staticmethod
    def chat_url(token: str) -> str:
        """The chatbot WebView URL (token appended like the app does)."""
        return f"{CHATBOT_CONTENT_URL}?token={token}"
