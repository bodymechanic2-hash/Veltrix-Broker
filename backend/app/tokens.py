"""One-time submission tokens.

Simulated orders and demo top-ups are state-changing forms. Even with the
post/redirect/get pattern, a fast double-click can submit the same form twice
before the first redirect is followed. To keep the demo's balances consistent,
each rendered form carries a short-lived, randomly generated token that the
server accepts exactly once.

Tokens live in the signed session cookie and are capped so a session cannot
grow without bound. This is a convenience safeguard for the demonstration, not
a substitute for real idempotency keys on a production ledger.
"""
from __future__ import annotations

import secrets

from flask import session

_TOKENS_KEY = "pending_tokens"
_MAX_PER_BUCKET = 20


def _store() -> dict[str, list[str]]:
    store = session.get(_TOKENS_KEY)
    if not isinstance(store, dict):
        store = {}
    return store


def issue_token(bucket: str) -> str:
    """Create and remember a fresh one-time token for ``bucket``."""
    token = secrets.token_urlsafe(24)
    store = _store()
    pending = store.get(bucket) or []
    pending.append(token)
    if len(pending) > _MAX_PER_BUCKET:
        del pending[: len(pending) - _MAX_PER_BUCKET]
    store[bucket] = pending
    session[_TOKENS_KEY] = store
    session.modified = True
    return token


def consume_token(bucket: str, token: str | None) -> bool:
    """Return True and invalidate ``token`` if it was issued for ``bucket``.

    A missing, unknown or already-used token returns False so the caller can
    reject the duplicate submission without changing any persisted state.
    """
    if not token:
        return False
    store = _store()
    pending = store.get(bucket) or []
    if token not in pending:
        return False
    pending.remove(token)
    store[bucket] = pending
    session[_TOKENS_KEY] = store
    session.modified = True
    return True
