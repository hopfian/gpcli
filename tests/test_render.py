"""Render primitives — shared formatting helpers."""

from gpcli.models import Me, Profile
from gpcli.render import action_ok, plural, render_action_response


def test_plural_singular():
    assert plural(1, "day") == "1 day"
    assert plural(1, "GP point") == "1 GP point"
    assert plural(1, "card") == "1 card"


def test_plural_plural():
    assert plural(0, "day") == "0 days"
    assert plural(2, "day") == "2 days"
    assert plural(56, "day") == "56 days"
    assert plural(120, "GP point") == "120 GP points"


class TestRenderMe:
    """`render_me` must survive payloads with and without the interests field."""

    def test_profile_without_rfu_1_does_not_crash(self, capsys):
        from gpcli.render.account import render_me

        me = Me(msisdn="8801700000000", profile=Profile(name="X"))
        render_me(me)  # used to raise AttributeError on rfu_1
        out = capsys.readouterr().out
        assert "interests" not in out  # row only shows when present

    def test_profile_with_rfu_1_shows_interests(self, capsys):
        from gpcli.render.account import render_me

        me = Me(
            msisdn="8801700000000",
            profile=Profile(name="X", rfu_1="sports,music"),
        )
        render_me(me)
        out = capsys.readouterr().out
        assert "interests" in out and "sports,music" in out


class TestRenderCardsNull:
    def test_null_cards_renders_empty(self, capsys):
        from gpcli.render.content import render_cards

        render_cards({"cards": None, "categories": None})  # no crash
        out = capsys.readouterr().out
        assert "0 cards" in out


class TestActionOk:
    """Envelope judging: status wins, bare code checks 200, non-envelope 2xx is ok."""

    def test_status_vocabulary(self):
        for ok in ("success", "pending", "accepted", "completed", "ok",
                   "active", "true", "SUCCESS", " Pending "):
            assert action_ok({"status": ok}), ok
        for bad in ("failed", "error", "rejected", "inactive"):
            assert not action_ok({"status": bad}), bad

    def test_status_beats_code(self):
        assert not action_ok({"code": 200, "status": "failed"})

    def test_bare_code(self):
        assert action_ok({"code": 200, "message": "done"})
        assert action_ok({"code": "200"})
        assert not action_ok({"code": 404, "message": "no"})

    def test_non_envelope_payload_is_ok(self):
        # HTTP errors raise in the client; a 2xx dict without status/code is success
        assert action_ok({"data": {"is_gp": True}})
        assert not action_ok(None)

    def test_message_extraction(self):
        # render_action_response pulls the first of the message-ish keys
        assert render_action_response(
            {"status": "success", "msg": "FnF added"}, title="t"
        )
        assert render_action_response(
            {"code": 500, "message": "boom"}, title="t"
        ) is False
