"""Symmetric encryption helpers for sensitive credentials (refresh tokens, etc.).

Uses Fernet (AES-128-CBC + HMAC-SHA256) with the key from settings.FERNET_KEY.
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = getattr(settings, "FERNET_KEY", "") or ""
    if not key:
        raise ImproperlyConfigured(
            "FERNET_KEY is not configured. Set it in .env. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    if isinstance(key, str):
        key = key.encode("utf-8")
    try:
        return Fernet(key)
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(f"FERNET_KEY is invalid: {exc}") from exc


def encrypt_str(plaintext: str) -> str:
    if plaintext is None:
        raise ValueError("Cannot encrypt None")
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_str(ciphertext: str) -> str:
    if not ciphertext:
        raise ValueError("Cannot decrypt empty ciphertext")
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid or tampered ciphertext") from exc


# Aliases with permissive semantics (None / empty pass through, tampered → None).
# Used by older modules and tests.
def encrypt_secret(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    return encrypt_str(value)


def decrypt_secret(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    try:
        return decrypt_str(value)
    except ValueError:
        return None
