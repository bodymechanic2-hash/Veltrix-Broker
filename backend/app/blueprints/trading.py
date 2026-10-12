"""Simulated (paper) trading, portfolio, activity and demo funds.

No order is ever sent to a broker, exchange or market. Cash and positions are
updated together in a single database transaction so they can never drift apart
when an order is rejected.
"""
from decimal import Decimal

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc

from ..extensions import db
from ..forms import TopUpForm, TradeForm
from ..models import Instrument, Position, Transaction, money, quantity
from ..tokens import consume_token, issue_token

bp = Blueprint("trading", __name__)


class TradeError(Exception):
    """A rejected simulated order. Never changes persisted state."""


def _position(user_id: int, instrument_id: int) -> Position | None:
    return Position.query.filter_by(user_id=user_id, instrument_id=instrument_id).first()


@bp.post("/trade")
@login_required
def trade():
    form = TradeForm()
    instrument = None
    if form.instrument_id.data and form.instrument_id.data.isdigit():
        instrument = db.session.get(Instrument, int(form.instrument_id.data))

    if not form.validate_on_submit() or instrument is None:
        message = " ".join(
            error for errors in form.errors.values() for error in errors
        ) or "Could not process the simulated order."
        flash(message, "error")
        return redirect(request.referrer or url_for("markets.index"))

    # Reject a replayed submission (e.g. a double-click) before changing state.
    if not consume_token("trade", form.submission_id.data):
        flash(
            "This simulated order was already submitted. Nothing was changed. "
            "Reload the instrument to place a new order.",
            "info",
        )
        return redirect(request.referrer or url_for("markets.index"))

    side = form.side.data
    qty = quantity(Decimal(form.quantity.data.strip()))
    price = instrument.price
    amount = money(qty * price)
    account = current_user.account

    try:
        with db.session.begin_nested():
            if side == "buy":
                if account is None:
                    raise TradeError("No demo account is available for this user.")
                if account.cash_balance < amount:
                    raise TradeError(
                        f"Insufficient demo balance. This buy needs {amount:.2f} "
                        f"{account.currency} but only {account.cash_balance:.2f} is available."
                    )
                pos = _position(current_user.id, instrument.id)
                if pos is None:
                    pos = Position(user_id=current_user.id, instrument_id=instrument.id)
                    db.session.add(pos)
                    pos.quantity = Decimal("0")
                    pos.avg_price = Decimal("0")
                total_cost = (pos.avg_price * pos.quantity) + amount
                new_qty = pos.quantity + qty
                pos.quantity = quantity(new_qty)
                pos.avg_price = (total_cost / new_qty).quantize(Decimal("0.00000001"))
                account.cash_balance = money(account.cash_balance - amount)
            else:
                pos = _position(current_user.id, instrument.id)
                if pos is None or pos.quantity < qty:
                    owned = pos.quantity if pos else Decimal("0")
                    raise TradeError(
                        f"You do not own enough {instrument.symbol} to sell. "
                        f"Available: {owned.normalize():f}."
                    )
                account.cash_balance = money(account.cash_balance + amount)
                remaining = pos.quantity - qty
                if remaining == 0:
                    db.session.delete(pos)
                else:
                    pos.quantity = quantity(remaining)

            db.session.add(
                Transaction(
                    user_id=current_user.id,
                    instrument_id=instrument.id,
                    symbol=instrument.symbol,
                    side=side,
                    quantity=qty,
                    execution_price=price,
                    amount=amount,
                    status="simulated",
                    note="Simulated paper order — not sent to any market.",
                )
            )
        db.session.commit()
    except TradeError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    except Exception:  # pragma: no cover - defensive; keeps balances consistent
        db.session.rollback()
        current_app.logger.exception("Simulated order failed")
        flash("The simulated order could not be processed. Nothing was changed.", "error")
    else:
        verb = "Bought" if side == "buy" else "Sold"
        flash(
            f"{verb} {qty.normalize():f} {instrument.symbol} at {price:.4f} "
            f"(simulated, {amount:.2f} {account.currency}). No real trade was executed.",
            "success",
        )
    return redirect(request.referrer or url_for("trading.portfolio"))


@bp.get("/portfolio")
@login_required
def portfolio():
    positions = [
        p for p in Position.query.filter_by(user_id=current_user.id).all() if p.quantity > 0
    ]
    positions.sort(key=lambda p: p.market_value, reverse=True)
    cash = money(current_user.account.cash_balance) if current_user.account else Decimal("0.00")
    portfolio_value = sum((p.market_value for p in positions), Decimal("0.00"))
    return render_template(
        "portfolio/index.html",
        positions=positions,
        cash=cash,
        portfolio_value=portfolio_value,
        total_equity=money(cash + portfolio_value),
        cost_basis=sum((p.cost_basis for p in positions), Decimal("0.00")),
        unrealised=sum((p.unrealised_pnl for p in positions), Decimal("0.00")),
        topup_form=TopUpForm(submission_id=issue_token("topup")),
    )


@bp.get("/transactions")
@login_required
def transactions():
    rows = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(desc(Transaction.created_at), desc(Transaction.id))
        .all()
    )
    return render_template("portfolio/transactions.html", transactions=rows)


@bp.post("/demo/top-up")
@login_required
def top_up():
    """Add fictional demo funds. Never touches a payment provider."""
    form = TopUpForm()
    account = current_user.account
    if form.validate_on_submit() and account is not None:
        if not consume_token("topup", form.submission_id.data):
            flash(
                "This demo top-up was already submitted. Reload the portfolio to add funds again.",
                "info",
            )
            return redirect(url_for("trading.portfolio"))
        amount = money(form.amount.data)
        try:
            with db.session.begin_nested():
                account.cash_balance = money(account.cash_balance + amount)
                db.session.add(
                    Transaction(
                        user_id=current_user.id,
                        instrument_id=None,
                        symbol=account.currency,
                        side="topup",
                        quantity=Decimal("0"),
                        execution_price=Decimal("0"),
                        amount=amount,
                        status="simulated",
                        note="Fictional demo funds — no money was deposited.",
                    )
                )
            db.session.commit()
        except Exception:  # pragma: no cover - defensive
            db.session.rollback()
            flash("Could not add demo funds.", "error")
        else:
            flash(
                f"Added {amount:.2f} in fictional demo funds. No money was deposited and "
                "no payment was processed.",
                "success",
            )
    else:
        flash("Enter an amount between 1 and 100000 to add demo funds.", "error")
    return redirect(url_for("trading.portfolio"))
