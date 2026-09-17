import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _master_key() -> bytes:
    return base64.urlsafe_b64decode(settings.credential_master_key.encode())


def encrypt(plaintext: str) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    aesgcm = AESGCM(_master_key())
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return ciphertext, nonce


def decrypt(ciphertext: bytes, nonce: bytes) -> str:
    aesgcm = AESGCM(_master_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
