"""Simulated trading rules: validation, balances, positions and activity."""
from decimal import Decimal

from conftest import get_csrf, get_tokens, instrument_id, login, register

from app.models import Position, Transaction, User


def _user(email="trader@example.com"):
    return User.query.filter_by(email=email).first()


def submit_trade(client, app, symbol, side, qty):
    csrf, submission = get_tokens(client, f"/markets/{symbol}")
    return client.post(
        "/trade",
        data={
            "csrf_token": csrf,
            "submission_id": submission or "",
            "instrument_id": str(instrument_id(app, symbol)),
            "side": side,
            "quantity": str(qty),
        },
        follow_redirects=True,
    )


def test_buy_updates_balance_and_position(client, app):
    register(client, email="trader@example.com")
    response = submit_trade(client, app, "AAPL", "buy", 2)
    assert response.status_code == 200

    user = _user()
    # 2 * 185.64 = 371.28
    assert user.account.cash_balance == Decimal("10000.00") - Decimal("371.28")
    pos = Position.query.filter_by(user_id=user.id).first()
    assert pos is not None
    assert pos.quantity == Decimal("2")
    assert Transaction.query.filter_by(user_id=user.id, side="buy").count() == 1


def test_insufficient_demo_balance_rejected(client, app):
    register(client, email="trader@example.com")
    response = submit_trade(client, app, "AAPL", "buy", 100000)
    body = response.get_data(as_text=True)
    assert "Insufficient demo balance" in body
    user = _user()
    assert user.account.cash_balance == Decimal("10000.00")
    assert Position.query.filter_by(user_id=user.id).count() == 0
    assert Transaction.query.count() == 0


def test_sell_more_than_owned_rejected(client, app):
    register(client, email="trader@example.com")
    submit_trade(client, app, "AAPL", "buy", 1)
    response = submit_trade(client, app, "AAPL", "sell", 5)
    assert "do not own enough" in response.get_data(as_text=True)
    user = _user()
    pos = Position.query.filter_by(user_id=user.id).first()
    assert pos.quantity == Decimal("1")
    assert Transaction.query.filter_by(side="sell").count() == 0


def test_sell_updates_position_and_cash(client, app):
    register(client, email="trader@example.com")
    submit_trade(client, app, "AAPL", "buy", 3)
    before = _user().account.cash_balance
    submit_trade(client, app, "AAPL", "sell", 1)
    user = _user()
    assert user.account.cash_balance == before + Decimal("185.64")
    pos = Position.query.filter_by(user_id=user.id).first()
    assert pos.quantity == Decimal("2")
    assert Transaction.query.filter_by(user_id=user.id, side="sell").count() == 1


def test_selling_all_closes_position(client, app):
    register(client, email="trader@example.com")
    submit_trade(client, app, "AAPL", "buy", 1)
    submit_trade(client, app, "AAPL", "sell", 1)
    user = _user()
    assert Position.query.filter_by(user_id=user.id).count() == 0


def test_invalid_quantities_rejected(client, app):
    register(client, email="trader@example.com")
    for bad in ["0", "-5", "abc", "1e999", ""]:
        response = submit_trade(client, app, "AAPL", "buy", bad)
        assert response.status_code == 200
    assert Position.query.count() == 0
    assert Transaction.query.count() == 0


def test_transaction_history_shows_activity(client, app):
    register(client, email="trader@example.com")
    submit_trade(client, app, "BTC/USD", "buy", "0.1")
    body = client.get("/transactions").get_data(as_text=True)
    assert "BTC/USD" in body
    assert "simulated".lower() in body.lower()


def test_demo_top_up_adds_fictional_funds(client, app):
    register(client, email="trader@example.com")
    csrf, submission = get_tokens(client, "/portfolio")
    response = client.post(
        "/demo/top-up",
        data={"csrf_token": csrf, "submission_id": submission or "", "amount": "500"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "no money was deposited" in response.get_data(as_text=True).lower()
    user = _user()
    assert user.account.cash_balance == Decimal("10500.00")
    assert Transaction.query.filter_by(user_id=user.id, side="topup").count() == 1


def test_replayed_trade_submission_is_ignored(client, app):
    register(client, email="trader@example.com")
    csrf, submission = get_tokens(client, "/markets/AAPL")
    payload = {
        "csrf_token": csrf,
        "submission_id": submission or "",
        "instrument_id": str(instrument_id(app, "AAPL")),
        "side": "buy",
        "quantity": "1",
    }
    first = client.post("/trade", data=payload, follow_redirects=True)
    assert first.status_code == 200
    assert Transaction.query.filter_by(side="buy").count() == 1

    # A second post that reuses the same one-time token must not place another order.
    second = client.post("/trade", data=payload, follow_redirects=True)
    assert second.status_code == 200
    assert "already submitted" in second.get_data(as_text=True).lower()
    assert Transaction.query.filter_by(side="buy").count() == 1
    assert _user().account.cash_balance == Decimal("10000.00") - Decimal("185.64")


def test_replayed_top_up_is_ignored(client, app):
    register(client, email="trader@example.com")
    csrf, submission = get_tokens(client, "/portfolio")
    payload = {"csrf_token": csrf, "submission_id": submission or "", "amount": "500"}
    client.post("/demo/top-up", data=payload, follow_redirects=True)
    client.post("/demo/top-up", data=payload, follow_redirects=True)
    user = _user()
    assert user.account.cash_balance == Decimal("10500.00")
    assert Transaction.query.filter_by(user_id=user.id, side="topup").count() == 1


def test_missing_submission_token_rejected(client, app):
    register(client, email="trader@example.com")
    csrf = get_csrf(client, "/markets/AAPL")
    response = client.post(
        "/trade",
        data={
            "csrf_token": csrf,
            "instrument_id": str(instrument_id(app, "AAPL")),
            "side": "buy",
            "quantity": "1",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert Transaction.query.count() == 0
    assert Position.query.count() == 0


def test_average_price_across_two_buys(client, app):
    register(client, email="trader@example.com")
    submit_trade(client, app, "AAPL", "buy", 1)
    submit_trade(client, app, "AAPL", "buy", 3)
    pos = Position.query.filter_by(user_id=_user().id).first()
    assert pos.quantity == Decimal("4")
    # Weighted average equals the instrument price because both buys used the same price.
    assert pos.avg_price == Decimal("185.64000000")
