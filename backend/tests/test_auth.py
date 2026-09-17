def register(client, email="a@example.com", password="password123"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def test_register_and_me(make_client):
    c = make_client()
    r = register(c)
    assert r.status_code == 201
    assert r.json()["email"] == "a@example.com"


def test_register_duplicate_email(make_client):
    c = make_client()
    register(c)
    r = register(c)
    assert r.status_code == 400


def test_login_sets_cookie_and_me(make_client):
    c = make_client()
    register(c)
    r = c.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in c.cookies
    me = c.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_login_wrong_password(make_client):
    c = make_client()
    register(c)
    r = c.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_me_requires_auth(make_client):
    c = make_client()
    assert c.get("/api/v1/auth/me").status_code == 401


def test_refresh(make_client):
    c = make_client()
    register(c)
    c.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})
    c.cookies.delete("access_token")
    r = c.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    assert "access_token" in c.cookies
