"""In-process tests for app/main.py's routes.

Every other test file in this project exercises the API by spawning a real
uvicorn subprocess (the fastapi_server fixture) and hitting it with requests.
That's realistic, but coverage.py can't see code that runs in a child
process, which is why app/main.py showed 0% despite being exercised by the
e2e suite. Using FastAPI's in-process TestClient here, with get_db and
get_current_active_user overridden to use the same test-database session and
a real seeded user, gets genuine line coverage without spinning up a server.
"""
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.conftest import run_async
from app.main import app, lifespan
from app.database import get_db
from app.auth.dependencies import get_current_active_user
from app.schemas.user import UserResponse
from app.models.calculation import Calculation
from app.models.user import User

STRONG_PASSWORD = "SecurePass123!"

# ======================================================================================
# Fixtures
# ======================================================================================

@pytest.fixture
def client(db_session):
    """A TestClient wired to the same test-database session used elsewhere.

    Deliberately not used as a context manager (`with TestClient(app) as c`),
    which would trigger the lifespan handler's Base.metadata.create_all(bind=engine)
    against the real DATABASE_URL engine rather than the test database. That's
    a harmless, idempotent call in practice, but there's no need to touch the
    dev database at all when the routes under test don't depend on it.
    """
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)

@pytest.fixture
def authed_client(client, test_user):
    """A client authenticated as `test_user`, bypassing real token verification.

    get_current_active_user's own logic (token decoding, active-user check)
    is already covered in tests/integration/test_dependencies.py; overriding
    it here isolates these tests to app/main.py's own route logic.
    """
    def override_current_user():
        return UserResponse.model_validate(test_user)
    app.dependency_overrides[get_current_active_user] = override_current_user
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)

# ======================================================================================
# Lifespan (startup table creation)
# ======================================================================================

def test_lifespan_creates_tables():
    """Test the lifespan handler creates tables on startup, without touching
    a real database: Base is mocked so metadata.create_all() is a no-op call
    we can just assert on.
    """
    async def enter_and_exit_lifespan():
        async with lifespan(app):
            pass

    with patch("app.main.Base") as mock_base:
        run_async(enter_and_exit_lifespan())

    mock_base.metadata.create_all.assert_called_once()

# ======================================================================================
# Web (HTML) routes
# ======================================================================================

def test_read_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to the Calculations App" in response.text

def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200

def test_register_page(client):
    response = client.get("/register")
    assert response.status_code == 200

def test_dashboard_page(client):
    response = client.get("/dashboard")
    assert response.status_code == 200

def test_view_calculation_page(client):
    response = client.get(f"/dashboard/view/{uuid4()}")
    assert response.status_code == 200

def test_edit_calculation_page(client):
    response = client.get(f"/dashboard/edit/{uuid4()}")
    assert response.status_code == 200

# ======================================================================================
# Health
# ======================================================================================

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# ======================================================================================
# Registration
# ======================================================================================

def test_register_success(client, fake_user_data):
    payload = {**fake_user_data, "password": STRONG_PASSWORD, "confirm_password": STRONG_PASSWORD}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["username"] == fake_user_data["username"]

def test_register_duplicate_user(client, fake_user_data):
    payload = {**fake_user_data, "password": STRONG_PASSWORD, "confirm_password": STRONG_PASSWORD}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400
    assert "already exists" in second.json()["detail"]

# ======================================================================================
# Login (JSON)
# ======================================================================================

def test_login_json_success(client, fake_user_data):
    payload = {**fake_user_data, "password": STRONG_PASSWORD, "confirm_password": STRONG_PASSWORD}
    client.post("/auth/register", json=payload)

    response = client.post(
        "/auth/login",
        json={"username": fake_user_data["username"], "password": STRONG_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body

def test_login_json_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        json={"username": "no_such_user", "password": "WrongPass123!"},
    )
    assert response.status_code == 401

def test_login_json_naive_expires_at_gets_utc_tzinfo(client, test_user):
    """Test the `expires_at.tzinfo is None` branch, which User.authenticate()
    never produces in practice (its utcnow() is always tz-aware) -- so we
    fake the auth_result the same way test_dependencies.py fakes verify_token.
    """
    naive_expiry = datetime(2030, 1, 1, 12, 0, 0)
    fake_auth_result = {
        "access_token": "fake-access-token",
        "refresh_token": "fake-refresh-token",
        "token_type": "bearer",
        "expires_at": naive_expiry,
        "user": test_user,
    }
    with patch("app.main.User.authenticate", return_value=fake_auth_result):
        response = client.post(
            "/auth/login",
            json={"username": test_user.username, "password": STRONG_PASSWORD},
        )
    assert response.status_code == 200
    assert response.json()["expires_at"].startswith("2030-01-01T12:00:00")

# ======================================================================================
# Login (form / Swagger)
# ======================================================================================

def test_login_form_success(client, fake_user_data):
    payload = {**fake_user_data, "password": STRONG_PASSWORD, "confirm_password": STRONG_PASSWORD}
    client.post("/auth/register", json=payload)

    response = client.post(
        "/auth/token",
        data={"username": fake_user_data["username"], "password": STRONG_PASSWORD},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_form_invalid_credentials(client):
    response = client.post(
        "/auth/token",
        data={"username": "no_such_user", "password": "WrongPass123!"},
    )
    assert response.status_code == 401

# ======================================================================================
# Calculations: Create
# ======================================================================================

def test_create_calculation_success(authed_client):
    response = authed_client.post("/calculations", json={"type": "addition", "inputs": [1, 2, 3]})
    assert response.status_code == 201
    assert response.json()["result"] == 6

def test_create_calculation_value_error_is_handled(authed_client):
    """Test the endpoint's own except ValueError branch.

    CalculationBase's own validators already reject anything that would make
    Calculation.create()/get_result() raise (bad type, too few inputs,
    division by zero), so that branch is unreachable through a legitimate
    request. Patch Calculation.create to force it, the same way earlier
    defense-in-depth branches were tested directly in this project.
    """
    with patch("app.main.Calculation.create", side_effect=ValueError("forced failure")):
        response = authed_client.post("/calculations", json={"type": "addition", "inputs": [1, 2]})
    assert response.status_code == 400
    assert "forced failure" in response.json()["detail"]

# ======================================================================================
# Calculations: List
# ======================================================================================

def test_list_calculations(authed_client):
    authed_client.post("/calculations", json={"type": "addition", "inputs": [1, 2]})
    response = authed_client.get("/calculations")
    assert response.status_code == 200
    assert len(response.json()) >= 1

# ======================================================================================
# Calculations: Get
# ======================================================================================

def test_get_calculation_success(authed_client):
    created = authed_client.post("/calculations", json={"type": "addition", "inputs": [1, 2]})
    calc_id = created.json()["id"]

    response = authed_client.get(f"/calculations/{calc_id}")
    assert response.status_code == 200
    assert response.json()["id"] == calc_id

def test_get_calculation_invalid_uuid(authed_client):
    response = authed_client.get("/calculations/not-a-uuid")
    assert response.status_code == 400

def test_get_calculation_not_found(authed_client):
    response = authed_client.get(f"/calculations/{uuid4()}")
    assert response.status_code == 404

# ======================================================================================
# Calculations: Update
# ======================================================================================

def test_update_calculation_success(authed_client):
    created = authed_client.post("/calculations", json={"type": "addition", "inputs": [1, 2]})
    calc_id = created.json()["id"]

    response = authed_client.put(f"/calculations/{calc_id}", json={"inputs": [10, 5]})
    assert response.status_code == 200
    assert response.json()["result"] == 15

def test_update_calculation_without_new_inputs(authed_client):
    """Test the `if calculation_update.inputs is not None` False branch: an
    empty update still succeeds and refreshes updated_at without touching result."""
    created = authed_client.post("/calculations", json={"type": "addition", "inputs": [1, 2]})
    calc_id = created.json()["id"]
    original_result = created.json()["result"]

    response = authed_client.put(f"/calculations/{calc_id}", json={})
    assert response.status_code == 200
    assert response.json()["result"] == original_result

def test_update_calculation_invalid_uuid(authed_client):
    response = authed_client.put("/calculations/not-a-uuid", json={"inputs": [1, 2]})
    assert response.status_code == 400

def test_update_calculation_not_found(authed_client):
    response = authed_client.put(f"/calculations/{uuid4()}", json={"inputs": [1, 2]})
    assert response.status_code == 404

# ======================================================================================
# Calculations: Delete
# ======================================================================================

def test_delete_calculation_success(authed_client):
    created = authed_client.post("/calculations", json={"type": "addition", "inputs": [1, 2]})
    calc_id = created.json()["id"]

    response = authed_client.delete(f"/calculations/{calc_id}")
    assert response.status_code == 204

def test_delete_calculation_invalid_uuid(authed_client):
    response = authed_client.delete("/calculations/not-a-uuid")
    assert response.status_code == 400

def test_delete_calculation_not_found(authed_client):
    response = authed_client.delete(f"/calculations/{uuid4()}")
    assert response.status_code == 404
