"""Synthetic test identifiers — the ONLY msisdn/auth-id values tests may use.

Real subscriber data (PII) is banned from this repo; every fixture and
assertion must reference these placeholders.
"""

from __future__ import annotations

MSISDN_880 = "8801700000000"  # canonical 13-char 880-format (GP 017 range)
MSISDN_LOCAL = "01700000000"  # local 11-digit form
MSISDN_NAKED = "1700000000"  # local without the leading 0
MSISDN_DASHED = "0170-000-0000"  # local with dashes
MSISDN_SPACED = f" {MSISDN_LOCAL} "  # whitespace-wrapped
MSISDN_PLUS = f"+{MSISDN_880}"
AUTH_ID = 100000001  # subscriber id
DEVICE_ID = "0123456789abcdef"  # synthetic 16-hex Android ID
DEVICE_MODEL = "Pixel 8"
DEVICE_MANUFACTURER = "Google"
