"""MSISDN normalization (server requires exactly 13 chars, 880-prefixed)."""

import pytest
from constants import (
    MSISDN_880,
    MSISDN_DASHED,
    MSISDN_LOCAL,
    MSISDN_NAKED,
    MSISDN_PLUS,
    MSISDN_SPACED,
)

from gpcli.errors import MsisdnFormatError
from gpcli.services.auth import normalize_msisdn


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (MSISDN_880, MSISDN_880),  # already canonical
        (MSISDN_LOCAL, MSISDN_880),  # local with leading 0
        (MSISDN_NAKED, MSISDN_880),  # local without leading 0
        (MSISDN_PLUS, MSISDN_880),  # with +
        (MSISDN_SPACED, MSISDN_880),  # whitespace
        (MSISDN_DASHED, MSISDN_880),  # dashes
    ],
)
def test_normalize(raw, expected):
    assert normalize_msisdn(raw) == expected


@pytest.mark.parametrize(
    "bad",
    [
        "12345",  # too short
        MSISDN_880 + "0",  # 14 digits
        "8802320548227",  # wrong operator prefix (not 8801…)
        "abcdefghijk",  # not digits
        "",
    ],
)
def test_rejects(bad):
    with pytest.raises(MsisdnFormatError):
        normalize_msisdn(bad)
