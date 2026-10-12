"""Authentication, access-control and health tests."""
from conftest import PASSWORD, create_user, get_csrf, login, logout, register

from app.models import DemoAccount, User


def test_landing_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "VELTRIX" in body
    assert "simulated" in body.lower()


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "up"
    assert data["mode"] == "simulation"


def test_register_creates_demo_account(client, app):
    response = register(client, email="newuser@example.com")
    assert response.status_code == 200
    user = User.query.filter_by(email="newuser@example.com").first()
    assert user is not None
    assert user.role == "client"
    assert user.account is not None
    assert user.account.cash_balance == 10000
    # Password must never be stored in plaintext.
    assert user.password_hash != PASSWORD
    assert PASSWORD not in user.password_hash


def test_duplicate_email_rejected(client, app):
    register(client, email="dupe@example.com")
    logout(client)
    response = register(client, email="dupe@example.com")
    assert response.status_code == 200
    assert "already exists" in response.get_data(as_text=True)
    assert User.query.filter_by(email="dupe@example.com").count() == 1


def test_registration_validation(client):
    token = get_csrf(client, "/register")
    # Mismatched passwords and short password should not create an account.
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Bad",
            "email": "bad@example.com",
            "password": "short",
            "confirm_password": "different",
        },
    )
    assert response.status_code == 200
    assert User.query.filter_by(email="bad@example.com").first() is None


def test_login_success_and_failure(client, app):
    create_user(app, "client@example.com")
    ok = login(client, "client@example.com")
    assert ok.status_code == 200
    assert "Welcome back" in ok.get_data(as_text=True) or "Dashboard" in ok.get_data(as_text=True)

    logout_resp = logout(client)
    assert logout_resp.status_code in (302, 200)

    bad = login(client, "client@example.com", password="wrong-password")
    assert "Invalid email or password" in bad.get_data(as_text=True)


def test_client_routes_require_login(client):
    for path in ["/dashboard", "/portfolio", "/transactions", "/support/"]:
        response = client.get(path)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_admin_routes_protected_from_clients(client, app):
    create_user(app, "client@example.com", role="client")
    login(client, "client@example.com")
    for path in ["/admin/", "/admin/users", "/admin/transactions", "/admin/support"]:
        response = client.get(path)
        assert response.status_code == 403


def test_admin_routes_redirect_anonymous(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_admin_user_can_access_admin(client, app):
    create_user(app, "admin@example.com", role="admin")
    login(client, "admin@example.com")
    response = client.get("/admin/")
    assert response.status_code == 200
    assert "Operations overview" in response.get_data(as_text=True)


def test_csrf_required_for_state_changes(client, app):
    create_user(app, "csrf@example.com")
    response = client.post(
        "/login", data={"email": "csrf@example.com", "password": PASSWORD}
    )
    assert response.status_code in (302, 400)
    # Login must not have succeeded without a CSRF token.
    assert client.get("/dashboard").status_code == 302


def test_admin_pages_never_expose_password_hashes(client, app):
    admin = create_user(app, "admin@example.com", role="admin")
    login(client, "admin@example.com")
    body = client.get("/admin/users").get_data(as_text=True)
    assert admin.password_hash not in body
    assert "scrypt" not in body and "pbkdf2" not in body


def test_logout_clears_client_access(client, app):
    register(client, email="logout@example.com")
    assert client.get("/dashboard").status_code == 200
    logout(client)
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_trade_and_watchlist_require_login(client, app):
    detail = client.get("/markets/AAPL")
    assert detail.status_code == 200
    assert "Sign in to trade" in detail.get_data(as_text=True)

    csrf = get_csrf(client, "/login")
    trade = client.post(
        "/trade",
        data={"csrf_token": csrf, "instrument_id": "1", "side": "buy", "quantity": "1"},
    )
    assert trade.status_code == 302
    assert "/login" in trade.headers["Location"]

    watch = client.post(
        "/markets/watchlist", data={"csrf_token": csrf, "instrument_id": "1"}
    )
    assert watch.status_code == 302
    assert "/login" in watch.headers["Location"]
