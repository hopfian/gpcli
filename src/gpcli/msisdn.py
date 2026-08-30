"""MSISDN format utilities (pure functions — no I/O, no state).

The MyGP backend requires subscriber numbers in exactly the 13-character
``8801XXXXXXXXX`` form ("The MSISDN must be 13 characters."), while several
endpoints want the local ``01XXXXXXXXX`` form instead. These helpers cover
both directions, faithful to the app's `ContactUtilsKt` normalization.
"""

from __future__ import annotations

import re

from gpcli.errors import MsisdnFormatError

_MSISDN_RE = re.compile(r"^8801\d{9}$")


def normalize_msisdn(value: str) -> str:
    """Normalize user input to the 13-character `8801XXXXXXXXX` format.

    Accepted: 8801XXXXXXXXX (13), 01XXXXXXXXX (11), 1XXXXXXXXX (10);
    optional `+`/spaces/dashes. The server rejects anything that is not
    exactly 13 characters ("The MSISDN must be 13 characters.").
    """
    digits = re.sub(r"[\s\-()+.]", "", value)
    if _MSISDN_RE.match(digits):
        return digits
    if re.match(r"^01\d{9}$", digits):
        return "880" + digits[1:]
    if re.match(r"^1\d{9}$", digits):
        return "880" + digits
    raise MsisdnFormatError(
        f"cannot normalize {value!r} to the 13-character 880-format "
        "(expected like 8801XXXXXXXXX, 01XXXXXXXXX or 1XXXXXXXXX)"
    )


def local_msisdn(value: str) -> str:
    """ContactUtilsKt normalization: strip non-digits, then a leading '88'."""
    digits = re.sub(r"\D", "", value)
    return re.sub(r"^88", "", digits)
