"""Symmetric encryption helpers for sensitive tenant secrets.

Uses Fernet (AES-128-CBC + HMAC SHA256). The key is read from the
`DJANGO_FERNET_KEY` env var. If absent, the helpers fall back to a key
derived from `SECRET_KEY` — fine for dev, but **production MUST set
DJANGO_FERNET_KEY**, otherwise rotating `SECRET_KEY` would invalidate
all stored tokens.
"""

from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    key = os.getenv('DJANGO_FERNET_KEY')
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    # Dev fallback: derive a Fernet key from SECRET_KEY.
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    derived = base64.urlsafe_b64encode(digest)
    return Fernet(derived)


def encrypt_secret(value: str | None) -> str | None:
    """Encrypt a UTF-8 string. None passes through."""
    if value is None or value == '':
        return value
    token = _get_fernet().encrypt(value.encode('utf-8'))
    return token.decode('ascii')


def decrypt_secret(value: str | None) -> str | None:
    """Decrypt a token produced by encrypt_secret. Returns None if invalid."""
    if value is None or value == '':
        return value
    try:
        plaintext = _get_fernet().decrypt(value.encode('ascii'))
    except (InvalidToken, ValueError):
        return None
    return plaintext.decode('utf-8')
