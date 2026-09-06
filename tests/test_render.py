"""Render primitives — shared formatting helpers."""

from gpcli.render import plural


def test_plural_singular():
    assert plural(1, "day") == "1 day"
    assert plural(1, "GP point") == "1 GP point"
    assert plural(1, "card") == "1 card"


def test_plural_plural():
    assert plural(0, "day") == "0 days"
    assert plural(2, "day") == "2 days"
    assert plural(56, "day") == "56 days"
    assert plural(120, "GP point") == "120 GP points"
