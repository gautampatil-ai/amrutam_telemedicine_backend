
def register(client, email="patient@example.com", password="correct-horse-battery-staple"):
    return client.post("/auth/register", json={"email":email,"password":password,"full_name":"Test Patient"})

def login(client, email="patient@example.com", password="correct-horse-battery-staple"):
    response = client.post("/auth/login", json={"email":email,"password":password})
    assert response.status_code == 200, response.text
    return {"Authorization":"Bearer "+response.json()["access_token"]}

def test_health_and_openapi(client):
    assert client.get("/health/live").json()["status"] == "ok"
    assert client.get("/openapi.json").status_code == 200

def test_register_login_and_duplicate_email(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    headers = login(client)
    assert client.get("/users/me", headers=headers).json()["email"] == "patient@example.com"

def test_bad_password_rejected(client):
    register(client)
    assert client.post("/auth/login", json={"email":"patient@example.com","password":"wrong-password"}).status_code == 401

def test_protected_endpoint_rejects_anonymous(client):
    assert client.get("/users/me").status_code == 401

def test_patient_cannot_access_admin_analytics(client):
    register(client)
    assert client.get("/admin/analytics", headers=login(client)).status_code == 403

def test_booking_requires_idempotency_key_and_patient_auth(client):
    register(client)
    headers = login(client)
    assert client.post("/consultations", json={"slot_id":1}, headers=headers).status_code == 422
    headers["Idempotency-Key"] = "booking-key-0001"
    assert client.post("/consultations", json={"slot_id":1}, headers=headers).status_code == 404

def test_rate_limited_api_has_metrics_endpoint(client):
    assert client.get("/metrics").status_code == 200
