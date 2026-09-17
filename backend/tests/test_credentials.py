from app.db.models import UserLlmCredential


def test_saved_key_metadata_and_replacement(make_client, db_session):
    client = make_client()
    account = {"email": "credential-test@example.com", "password": "test-password-123"}
    assert client.post("/api/v1/auth/register", json=account).status_code == 201
    assert client.post("/api/v1/auth/login", json=account).status_code == 200
    endpoint = "/api/v1/credentials/deepseek"
    first = client.put(endpoint, json={"api_key": "sk-test-only-1111"})
    assert first.status_code == 200
    saved = first.json()
    assert saved["last4"] == "1111"
    assert saved["created_at"] and saved["updated_at"]
    assert "sk-test-only" not in first.text
    replaced = client.put(endpoint, json={"api_key": "sk-test-only-2222"}).json()
    assert replaced["last4"] == "2222"
    assert replaced["created_at"] == saved["created_at"]
    assert replaced["validated"] is False
    assert client.get(endpoint).json() == replaced
    with db_session() as session:
        assert session.query(UserLlmCredential).count() == 1
    other = make_client()
    assert other.get(endpoint).status_code == 401
    removed = client.delete(endpoint).json()
    assert removed["configured"] is False
    assert removed["created_at"] is None
    assert client.get(endpoint).json()["last4"] is None
