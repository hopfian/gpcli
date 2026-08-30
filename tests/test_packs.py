"""Pack category predicates and PackItem helpers."""


from gpcli.models import PackItem
from gpcli.services.catalog import _in_category, _sort_packs


def _pack(**overrides) -> PackItem:
    base = {"id": "1", "type": "internet", "title": "Test", "keyword": "K", "price": "10"}
    base.update(overrides)
    return PackItem.model_validate(base)


class TestCategoryPredicates:
    def test_type_categories(self):
        assert _in_category("internet", _pack(type="internet"))
        assert not _in_category("internet", _pack(type="voice"))
        assert _in_category("bundles", _pack(type="bundle"))
        assert _in_category("minutes", _pack(type="voice"))
        assert _in_category("sms", _pack(type="sms"))
        assert _in_category("cashback", _pack(type="recharge_offer"))

    def test_gifts(self):
        assert _in_category("gifts", _pack(attributes=["giftable_offer"]))
        assert _in_category("gifts", _pack(attributes=["gift_only_offer"]))
        assert _in_category("gifts", _pack(attributes=["recharge_giftable_offer"]))
        assert not _in_category("gifts", _pack(attributes=["eb_eligible_offer"]))

    def test_rate_cutter(self):
        assert _in_category("rate-cutter", _pack(attributes=["rate_cutter_offer"]))
        assert _in_category("rate-cutter", _pack(attributes=["free_rate_cutter_offer"]))
        assert not _in_category("rate-cutter", _pack(type="internet"))

    def test_roaming_taka_vs_usd(self):
        bdt = _pack(attributes=["roaming_offer"], filters=["roaming_mobile_balance", "30_days"])
        usd = _pack(attributes=["roaming_offer"], filters=["Buy_with_USD", "30_days"])
        plain = _pack(attributes=["roaming_offer"])
        assert _in_category("roaming", bdt)
        assert not _in_category("roaming", bdt, usd=True)
        assert _in_category("roaming", usd, usd=True)
        assert not _in_category("roaming", usd)
        assert _in_category("roaming", plain)  # unspecified currency defaults to Taka
        assert not _in_category("roaming", _pack(type="internet"))

    def test_entertainment(self):
        assert _in_category("entertainment", _pack(attributes=["entertainment_offer"]))
        assert _in_category("entertainment", _pack(filters=["hoichoi", "30_days"]))
        assert _in_category("entertainment", _pack(filters=["sonyliv"]))
        assert not _in_category("entertainment", _pack(filters=["internet", "daily"]))

    def test_subscriptions(self):
        assert _in_category("subscriptions", _pack(type="subscription"))
        assert _in_category("subscriptions", _pack(attributes=["subscription_item"]))
        assert not _in_category("subscriptions", _pack(type="bundle"))

    def test_all_matches_everything(self):
        assert _in_category("all", _pack(type="whatever"))
        assert _in_category("all", _pack())


class TestPackHelpers:
    def test_price_value(self):
        assert _pack(price="1049").price_value == 1049.0
        assert _pack(price="").price_value is None
        assert _pack(price="abc").price_value is None

    def test_volume_summary(self):
        p = _pack(volume={
            "internet": {"value": "25600", "unit": "MB"},
            "voice": {"value": "300", "unit": "Minutes"},
            "sms": {"value": "0", "unit": "SMS"},
        })
        assert p.volume_summary() == "25600 MB · 300 Minutes"

    def test_validity_summary(self):
        assert _pack(validity={"value": "30", "unit": "days"}).validity_summary() == "30 days"
        unlimited = _pack(validity={"value": "", "unit": "Unlimited Validity"})
        assert unlimited.validity_summary() == "Unlimited Validity"
        assert _pack().validity_summary() == ""

    def test_cashback_text(self):
        p = _pack(additional_data={"cashback_text": "Get 20 Tk back"})
        assert p.cashback_text() == "Get 20 Tk back"
        p2 = _pack(additional_data={"digital_payment_cashback": {"text": "5% on cards"}})
        assert p2.cashback_text() == "5% on cards"
        assert _pack().cashback_text() == ""


class TestSortPacks:
    def test_price_ascending_non_numeric_last(self):
        a, b, c, bad = _pack(price="20"), _pack(price="10"), _pack(price="99"), _pack(price="")
        assert _sort_packs([bad, c, a, b]) == [b, a, c, bad]
