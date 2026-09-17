from app.core import encryption


def test_encrypt_decrypt_roundtrip():
    ct, nonce = encryption.encrypt("sk-1234567890abcdef")
    assert ct != b"sk-1234567890abcdef"
    assert encryption.decrypt(ct, nonce) == "sk-1234567890abcdef"


def test_encrypt_is_nondeterministic():
    ct1, _ = encryption.encrypt("same")
    ct2, _ = encryption.encrypt("same")
    assert ct1 != ct2
