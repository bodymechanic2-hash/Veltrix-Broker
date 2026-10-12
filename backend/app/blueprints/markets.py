"""Markets list, instrument detail and watchlist controls."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from ..extensions import db
from ..forms import TradeForm, WatchlistForm
from ..models import Instrument, WatchlistItem
from ..tokens import issue_token

bp = Blueprint("markets", __name__, url_prefix="/markets")


def _asset_classes():
    rows = (
        db.session.query(Instrument.asset_class)
        .filter_by(is_active=True)
        .distinct()
        .order_by(Instrument.asset_class)
        .all()
    )
    return [r[0] for r in rows]


def _watchlist_symbols() -> set[str]:
    if not current_user.is_authenticated:
        return set()
    rows = (
        db.session.query(Instrument.symbol)
        .join(WatchlistItem, WatchlistItem.instrument_id == Instrument.id)
        .filter(WatchlistItem.user_id == current_user.id)
        .all()
    )
    return {r[0] for r in rows}


@bp.get("/")
def index():
    query = (request.args.get("q") or "").strip()
    asset = (request.args.get("asset") or "").strip()

    stmt = Instrument.query.filter_by(is_active=True)
    if query:
        like = f"%{query.lower()}%"
        stmt = stmt.filter(
            or_(func.lower(Instrument.symbol).like(like), func.lower(Instrument.name).like(like))
        )
    if asset:
        stmt = stmt.filter(Instrument.asset_class == asset)
    instruments = stmt.order_by(Instrument.asset_class, Instrument.symbol).all()

    return render_template(
        "markets/index.html",
        instruments=instruments,
        query=query,
        asset=asset,
        asset_classes=_asset_classes(),
        watchlist=_watchlist_symbols(),
        form=TradeForm(),
    )


@bp.get("/<path:symbol>")
def detail(symbol: str):
    instrument = Instrument.query.filter_by(symbol=symbol.upper(), is_active=True).first()
    if instrument is None:
        abort(404)
    form = TradeForm(instrument_id=instrument.id)
    if current_user.is_authenticated:
        # One-time token so a double-submit cannot place the same order twice.
        form.submission_id.data = issue_token("trade")
    return render_template(
        "markets/detail.html",
        instrument=instrument,
        watchlist=_watchlist_symbols(),
        form=form,
    )


@bp.post("/watchlist")
@login_required
def toggle_watchlist():
    form = WatchlistForm()
    if not form.validate_on_submit():
        flash("Could not update your watchlist. Please try again.", "error")
        return redirect(request.referrer or url_for("markets.index"))
    instrument = db.session.get(Instrument, int(form.instrument_id.data))
    if instrument is None:
        abort(404)
    existing = WatchlistItem.query.filter_by(
        user_id=current_user.id, instrument_id=instrument.id
    ).first()
    if existing:
        db.session.delete(existing)
        flash(f"{instrument.symbol} removed from your watchlist.", "info")
    else:
        db.session.add(WatchlistItem(user_id=current_user.id, instrument_id=instrument.id))
        flash(f"{instrument.symbol} added to your watchlist.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("markets.index"))
