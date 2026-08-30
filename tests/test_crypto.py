"""EncryptionUtil replication — AES-256-CTR, static and silent-login keys."""

import pytest

from gpcli.crypto import (
    STATIC_IV,
    STATIC_KEY,
    _aes_ctr,
    build_silent_login,
    decrypt_hex,
    decrypt_static,
    encrypt_hex,
    encrypt_static,
    silent_login_body,
)


def test_static_roundtrip():
    plaintext = "some server payload"
    ciphertext = encrypt_static(plaintext)
    assert ciphertext == _aes_ctr(STATIC_KEY, STATIC_IV, plaintext.encode()).hex()
    assert decrypt_static(ciphertext) == plaintext


def test_static_hex_is_lowercase():
    assert encrypt_static("A") == encrypt_static("A").lower()
    assert len(encrypt_static("0123456789abcdef")) == 32


def test_ctr_is_symmetric():
    data = b"x" * 100  # multi-block
    ct = _aes_ctr(STATIC_KEY, STATIC_IV, data)
    assert _aes_ctr(STATIC_KEY, STATIC_IV, ct) == data


def test_ctr_keystream_reuse_fails():
    # identical IV+key must produce identical keystream (CTR property the app relies on)
    a = _aes_ctr(STATIC_KEY, STATIC_IV, b"hello")
    b = _aes_ctr(STATIC_KEY, STATIC_IV, b"world")
    assert bytes(x ^ y for x, y in zip(a, b"hello", strict=False)) == bytes(
        x ^ y for x, y in zip(b, b"world", strict=False)
    )


class TestBuildSilentLogin:
    def test_deterministic_pieces(self):
        spec = build_silent_login("0123456789abcdef", "CODECODECODECODE", timestamp=1788150000, idx=3)
        # ts = "1788150000", ts[3:5] = "81"; code[3:5] = "EC"
        km = b"mygp" + b"81" + b"grameenp" + b"EC"
        expected = encrypt_hex("0123456789abcdef", iv=km, key=km + km)
        assert spec.hash == f"3{expected}"
        assert spec.timestamp == "1788150000"
        assert spec.code == "CODECODECODECODE"

    def test_key_material_length(self):
        spec = build_silent_login("dev", "0123456789abcdef0123456789abcdef", timestamp=1788150000, idx=5)
        # decrypt the hash back using the same derivation — proves the wire format
        idx = int(spec.hash[0])
        ts = spec.timestamp
        code = spec.code
        km = ("mygp" + ts[idx : idx + 2] + "grameenp" + code[idx : idx + 2]).encode()
        assert len(km) == 16
        assert decrypt_hex(spec.hash[1:], iv=km, key=km + km) == "dev"

    def test_short_code_raises(self):
        with pytest.raises(ValueError):
            build_silent_login("dev", "AB", timestamp=1788150000, idx=3)

    def test_body_shape(self):
        spec = build_silent_login("dev", "0123456789abcdef0123456789abcdef", timestamp=1788150000, idx=5)
        body = silent_login_body(spec, app_version="5.31.0", device_model="Pixel 8", device_name="Google")
        assert body == {
            "code": spec.code,
            "device_id": "dev",
            "hash": spec.hash,
            "timestamps": spec.timestamp,
            "app_version": "5.31.0",
            "device_model": "Pixel 8",
            "device_name": "Google",
        }


def test_encrypt_hex_validates_key_and_iv_lengths():
    with pytest.raises(ValueError):
        encrypt_hex("x", iv=b"short", key=STATIC_KEY)
    with pytest.raises(ValueError):
        encrypt_hex("x", iv=STATIC_IV, key=b"short")
