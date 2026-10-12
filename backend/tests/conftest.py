"""Pytest fixtures and helpers for the VELTRIX demo test-suite."""
import re
import sys
from pathlib import Path

import pytest

# Make the backend package importable when running `pytest` from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import DemoAccount, Instrument, User, money  # noqa: E402
from app.seed import seed_instruments  # noqa: E402

CSRF_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')
SUBMISSION_RE = re.compile(r'name="submission_id"[^>]*value="([^"]+)"')

PASSWORD = "DemoPass123!"


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        seed_instruments()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def get_csrf(client, path="/login"):
    response = client.get(path)
    match = CSRF_RE.search(response.get_data(as_text=True))
    assert match, f"No CSRF token found on {path}"
    return match.group(1)


def get_tokens(client, path):
    """Return the CSRF token and one-time submission token rendered on a page."""
    response = client.get(path)
    html = response.get_data(as_text=True)
    csrf = CSRF_RE.search(html)
    assert csrf, f"No CSRF token found on {path}"
    submission = SUBMISSION_RE.search(html)
    return csrf.group(1), (submission.group(1) if submission else None)


def register(client, name="Test User", email="test@example.com", password=PASSWORD, agree="y"):
    token = get_csrf(client, "/register")
    return client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
            "agree": agree,
        },
        follow_redirects=True,
    )


def login(client, email="test@example.com", password=PASSWORD):
    token = get_csrf(client, "/login")
    return client.post(
        "/login",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=True,
    )


def logout(client):
    token = _meta_csrf(client)
    return client.post("/logout", data={"csrf_token": token}, follow_redirects=True)


def _meta_csrf(client, path="/dashboard"):
    response = client.get(path)
    match = CSRF_RE.search(response.get_data(as_text=True))
    return match.group(1) if match else ""


def create_user(app, email, password=PASSWORD, role="client", name="Seed User", balance="10000.00"):
    user = User(name=name, email=email, role=role)
    user.set_password(password)
    user.account = DemoAccount(currency="USD", cash_balance=money(balance))
    db.session.add(user)
    db.session.commit()
    return user


def instrument_id(app, symbol):
    return Instrument.query.filter_by(symbol=symbol).first().id
