"""Flexiplan bundle-key/price encoding and VAS model tests."""

import pytest

from gpcli.errors import MyGPError
from gpcli.models import FlexiPlan, PackItem
from gpcli.services.catalog import (
    CatalogService,
    build_bundle_key,
    parse_bundle_price,
    quote_flexiplan,
)
from gpcli.services.netcare import NetworkComplainService

CATALOG = FlexiPlan.model_validate({
    "hash": "abc",
    "mca_price": {"prepaid": 7.5, "postpaid": 0},
    "mca_market_price": {"prepaid": 11, "postpaid": 0},
    "vat": {"dataOnly": 1.39, "mixed": 1.39},
    "map": {
        "data": [0, 3072, 5120], "voice": [0, 10, 25], "sms": [0, 50, 100],
        "bioscope": [0, 1024], "days": [1, 3, 7, 30], "mca": [0, 1],
    },
    "selected": {"voice": 300, "data": 30720, "bioscope": 0, "4G": 0, "sms": 0, "mca": 0, "days": 30},
    "bundles": {
        "L3_V0_D0M_F0M_B0M_S50": "B0_M9.76_C0_T10_P23.56_S10_D26",
        "L30_V300_D30G_F0M_B0M_S0": "B42_M50_C1_T58.38_P58.38_S0_D0",
    },
})


class TestBundleKey:
    def test_format(self):
        assert build_bundle_key(30, 300, 30720, 0, 0, 0) == "L30_V300_D30G_F0M_B0M_S0"

    def test_zeroes(self):
        assert build_bundle_key(1) == "L1_V0_D0M_F0M_B0M_S0"

    def test_all_components(self):
        key = build_bundle_key(7, 25, 5120, 1024, 2048, 100)
        assert key == "L7_V25_D5G_F1G_B2G_S100"

    def test_sub_gb_values_use_m_suffix(self):
        assert build_bundle_key(3, 0, 512) == "L3_V0_D512M_F0M_B0M_S0"


class TestParseBundlePrice:
    def test_real_payload(self):
        price = parse_bundle_price("B0_M9.76_C0_T10_P23.56_S10_D26")
        assert price.base_price == 0
        assert price.market_price == 9.76
        assert price.base_price_vat == 10
        assert price.price_vat_mca_prepaid == 23.56
        assert price.price_vat_mca_postpaid == 10
        assert price.discount_percent == 26

    def test_discount_ceiling(self):
        # app uses Math.ceil — 26.1 must round up to 27
        assert parse_bundle_price("D26.1").discount_percent == 27
        assert parse_bundle_price("D0").discount_percent == 0

    def test_partial_and_garbage(self):
        price = parse_bundle_price("B1.5")
        assert price.base_price == 1.5
        assert parse_bundle_price("nope_x_y").base_price == 0


class TestQuote:
    def test_lookup(self):
        key, price = quote_flexiplan(CATALOG, 3, sms=50)
        assert key == "L3_V0_D0M_F0M_B0M_S50"
        assert price.price_vat_mca_prepaid == 23.56

    def test_lookup_gb_values(self):
        key, price = quote_flexiplan(CATALOG, 30, voice=300, data_mb=30720)
        assert key == "L30_V300_D30G_F0M_B0M_S0"
        assert price.price_vat_mca_prepaid == 58.38

    def test_missing_key_raises_mygp_error(self):
        from gpcli.errors import MyGPError

        with pytest.raises(MyGPError, match="L99"):
            quote_flexiplan(CATALOG, 99)


class TestNullDataHardening:
    """`{"data": null}` must degrade to empty, never crash the comprehension."""

    def test_vas_categories_null_data(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/vas/get-categories", json={"data": None})
        assert CatalogService(client).vas_categories() == []

    def test_vas_services_null_data(self, make_client):
        client, rec = make_client()
        rec.add("GET", "/vas/get-services", json={"data": None})
        assert CatalogService(client).vas_services(1) == []

    def test_validity_summary_none_unit(self):
        pack = PackItem.model_validate({
            "pack_id": 1, "pack_name": "x", "price": 5,
            "validity": {"value": "30", "unit": None},
        })
        assert pack.validity_summary() == "30"  # not "30 None"

    def test_validity_summary_valueless_unit_only(self):
        pack = PackItem.model_validate({
            "pack_id": 1, "pack_name": "x", "price": 5,
            "validity": {"value": None, "unit": "Days"},
        })
        assert pack.validity_summary() == "Days"  # a str, never None

    def test_netcare_submit_missing_answer_key(self, make_client):
        client, rec = make_client()
        service = NetworkComplainService(client)
        with pytest.raises(MyGPError, match="missing feedback"):
            service.submit([{"id": 1, "type": "textarea"}])


class TestFlexiPlanModel:
    def test_alias_parsing(self):
        assert CATALOG.selected.days == 30
        assert CATALOG.selected.voice == 300
        assert CATALOG.map.data == [0, 3072, 5120]
        assert CATALOG.mca_price["prepaid"] == 7.5
