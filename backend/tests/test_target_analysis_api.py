def _register_login(client):
    account = {"email": "ta-test@example.com", "password": "test-password-123"}
    client.post("/api/v1/auth/register", json=account)
    client.post("/api/v1/auth/login", json=account)


def _create_project(client):
    r = client.post("/api/v1/projects", json={"name": "测试项目", "primary_disease": "阿尔茨海默病"})
    return r.json()["id"]


def test_catalog_requires_auth(make_client):
    assert make_client().get("/api/v1/target-analysis/catalog").status_code == 401


def test_catalog_returns_diseases(make_client):
    c = make_client()
    _register_login(c)
    r = c.get("/api/v1/target-analysis/catalog")
    assert r.status_code == 200
    body = r.json()
    assert body["version"]
    assert len(body["diseases"]) >= 1
    assert body["diseases"][0]["id"]


def test_create_run_unknown_disease(make_client):
    c = make_client()
    _register_login(c)
    pid = _create_project(c)
    r = c.post("/api/v1/target-analysis/runs", json={
        "project_id": pid, "disease_id": "MONDO_UNKNOWN", "question": "x" * 20,
    })
    assert r.status_code == 400


def test_create_run_without_credential(make_client):
    c = make_client()
    _register_login(c)
    pid = _create_project(c)
    disease_id = c.get("/api/v1/target-analysis/catalog").json()["diseases"][0]["id"]
    r = c.post("/api/v1/target-analysis/runs", json={
        "project_id": pid, "disease_id": disease_id, "question": "x" * 20,
    })
    assert r.status_code == 400


def test_get_run_not_found(make_client):
    c = make_client()
    _register_login(c)
    r = c.get("/api/v1/target-analysis/runs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_rerank_invalid_weights(make_client):
    c = make_client()
    _register_login(c)
    r = c.post("/api/v1/target-analysis/runs/00000000-0000-0000-0000-000000000000/rerank",
               json={"w_a": 0.8, "w_n": 0.5})
    assert r.status_code == 422
