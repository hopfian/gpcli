"""Error taxonomy for gpcli."""


class MyGPError(Exception):
    """Base error for all gpcli failures."""


class AuthRequiredError(MyGPError):
    """No subscriber session — run `gpcli login <msisdn>` first."""


class AuthExpiredError(MyGPError):
    """Server rejected the session (401/911/410) and it was cleared."""


class ApiError(MyGPError):
    """ErrorV2 envelope returned by the API: {"error": {code, reason, ...}}."""

    def __init__(self, code: str | int | None, message: str, description: str | None = None):
        self.code = code
        self.message = message
        self.description = description
        super().__init__(f"[{code}] {message}" + (f" ({description})" if description else ""))


class GuestFlowError(MyGPError):
    """Guest login / guest token minting failed."""


class SilentLoginUnavailable(MyGPError):
    """Silent SIM login is gated to Grameenphone mobile-data IPs (nginx 403)."""


class MsisdnFormatError(MyGPError):
    """MSISDN could not be normalized to the required 13-character 880-format."""
