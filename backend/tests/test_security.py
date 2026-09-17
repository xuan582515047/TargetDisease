from app.core import security


def test_hash_and_verify_password():
    h = security.hash_password("secret123")
    assert h != "secret123"
    assert security.verify_password("secret123", h) is True
    assert security.verify_password("wrong", h) is False


def test_access_token_roundtrip():
    token = security.create_access_token("some-user-id")
    assert security.decode_token(token, "access") == "some-user-id"


def test_refresh_token_rejected_as_access():
    token = security.create_refresh_token("some-user-id")
    try:
        security.decode_token(token, "access")
        assert False, "should have raised"
    except Exception:
        pass
