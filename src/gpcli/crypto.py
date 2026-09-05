"""Replication of MyGP's client-side crypto (`com.mygp.utils.EncryptionUtil`).

The app uses AES-256-CTR (NoPadding) with hex-encoded ciphertext in two modes:

* **Static keys** — a key/IV pair hardcoded in the app
  (``Lk5Uz3slx3BrAghS1=aW5AYgWZRV0tIX`` / ``6119443eb39dc954``).
  Used to decrypt server-issued opaque payloads.

* **Dynamic keys** — the silent SIM login derives 16 bytes of key material
  from a timestamp and a server-issued code
  (``"mygp" + ts[idx:idx+2] + "grameenp" + code[idx:idx+2]``),
  then uses it as the IV and its doubling as the key. See `build_silent_login`.

Java's ``AES/CTR/NoPadding`` with a 16-byte ``IvParameterSpec`` treats the IV as
the full initial counter block, incremented big-endian per block — which is
byte-for-byte equivalent to ``cryptography``'s CTR mode with a 16-byte nonce.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

STATIC_KEY = b"Lk5Uz3slx3BrAghS1=aW5AYgWZRV0tIX"
STATIC_IV = b"6119443eb39dc954"

# AnalyticsIdUtil's own pair (used to derive the X-Analytics-ID header):
# hex(AES-CTR(msisdn, iv=ANALYTICS_IV, key=ANALYTICS_KEY)); the setting key
# it is stored under is Utils.T(msisdn) = MD5(msisdn).hex().
ANALYTICS_KEY = b"1234567890abcdef1234567890abcdef"
ANALYTICS_IV = b"1234567890abcdef"


def analytics_id(msisdn: str) -> str:
    """X-Analytics-ID — AnalyticsIdUtil.b()/a() over the auth msisdn."""
    return encrypt_hex(msisdn, ANALYTICS_IV, ANALYTICS_KEY)


def _aes_ctr(key: bytes, iv: bytes, data: bytes) -> bytes:
    if len(key) not in (16, 24, 32):
        raise ValueError(f"AES key must be 16/24/32 bytes, got {len(key)}")
    if len(iv) != 16:
        raise ValueError(f"CTR IV must be 16 bytes, got {len(iv)}")
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv))
    enc = cipher.encryptor()
    return enc.update(data) + enc.finalize()


def encrypt_hex(plaintext: str, iv: bytes, key: bytes) -> str:
    """EncryptionUtil.b(): AES-CTR encrypt, hex-encode (lowercase)."""
    return _aes_ctr(key, iv, plaintext.encode()).hex()


def decrypt_hex(hex_ciphertext: str, iv: bytes = STATIC_IV, key: bytes = STATIC_KEY) -> str:
    """EncryptionUtil.a(): hex-decode, AES-CTR decrypt, UTF-8 decode."""
    raw = bytes.fromhex(hex_ciphertext)
    return _aes_ctr(key, iv, raw).decode()


def encrypt_static(plaintext: str) -> str:
    return encrypt_hex(plaintext, STATIC_IV, STATIC_KEY)


def decrypt_static(hex_ciphertext: str) -> str:
    return decrypt_hex(hex_ciphertext, STATIC_IV, STATIC_KEY)


@dataclass(frozen=True)
class SilentLoginSpec:
    """Wire payload pieces for POST /v2/code (silent SIM login)."""

    code: str
    device_id: str
    timestamp: str  # unix seconds, as string
    hash: str  # str(idx) + hex(AES-CTR(device_id))


def build_silent_login(device_id: str, server_code: str, *, timestamp: int | None = None,
                       idx: int | None = None) -> SilentLoginSpec:
    """Replicate `LoginViewModel.c()` (verified against smali):

        ts  = str(unix_seconds)
        idx = random 0..len(ts)-3                      # Java nextInt(len(ts)-2)
        km  = "mygp" + ts[idx:idx+2] + "grameenp" + code[idx:idx+2]   # 16 bytes
        enc = AES-CTR(device_id, iv=km, key=km+km).hex()
        hash = str(idx) + enc
    """
    if not server_code:
        raise ValueError("server_code is empty")
    ts = str(timestamp if timestamp is not None else int(time.time()))
    if idx is None:
        idx = random.randrange(len(ts) - 2) if len(ts) > 2 else 0
    if idx < 0 or idx + 2 > len(ts):
        raise ValueError(f"idx {idx} out of range for timestamp {ts!r}")
    if idx + 2 > len(server_code):
        raise ValueError(f"server_code too short: need >= {idx + 2} chars, got {len(server_code)}")

    km = ("mygp" + ts[idx : idx + 2] + "grameenp" + server_code[idx : idx + 2]).encode()
    if len(km) != 16:
        raise ValueError(f"derived key material must be 16 bytes, got {len(km)}")
    encrypted = encrypt_hex(device_id, iv=km, key=km + km)
    return SilentLoginSpec(
        code=server_code,
        device_id=device_id,
        timestamp=ts,
        hash=f"{idx}{encrypted}",
    )


def silent_login_body(spec: SilentLoginSpec, *, app_version: str, device_model: str,
                      device_name: str) -> dict[str, str]:
    """POST /v2/code body (AuthRepository.l -> postCode)."""
    return {
        "code": spec.code,
        "device_id": spec.device_id,
        "hash": spec.hash,
        "timestamps": spec.timestamp,
        "app_version": app_version,
        "device_model": device_model,
        "device_name": device_name,
    }
