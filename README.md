# VELTRIX — Brokerage Demonstration Platform

VELTRIX is a **demonstration** multi-asset investment platform for EU-facing customers.
It pairs the original static marketing site with a real **Flask + SQLite** backend that
provides authentication, demo accounts, paper trading, portfolios, a support queue and an
administrator dashboard.

> **This is a demo, not a real brokerage.** All prices, balances, orders and transactions
> are **simulated**. No real money is received, held, deposited, withdrawn or invested.
> No order is sent to any broker, exchange or market. Nothing here is investment advice.

---

## 1. What is in this repository

| Area | Path | Description |
| --- | --- | --- |
| Static marketing site (GitHub Pages) | `index.html`, `styles.css`, `app.js` | The original premium concept landing site. Preserved and lightly corrected. |
| Full-stack demo backend | `backend/` | Flask application: auth, demo trading, portfolio, support, admin, JSON API. |

```
Veltrix-Broker/
├── index.html            # GitHub Pages static concept site
├── styles.css            # static site styles
├── app.js                # static site interactions (+ optional link to the backend)
├── .gitignore
├── backend/
│   ├── run.py            # development entry point
│   ├── wsgi.py           # production WSGI entry point
│   ├── config.py         # environment-driven configuration
│   ├── requirements.txt
│   ├── requirements-prod.txt   # gunicorn / waitress / psycopg for deployment
│   ├── Procfile          # process definition for PaaS hosts
│   ├── render.yaml       # example Render blueprint (backend only)
│   ├── .env.example
│   ├── pytest.ini
│   ├── app/
│   │   ├── __init__.py   # application factory
│   │   ├── extensions.py # db / login / csrf
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── forms.py      # WTForms (server-side validation + CSRF)
│   │   ├── tokens.py     # one-time submission tokens (anti double-submit)
│   │   ├── seed.py       # demo instruments + optional dev admin
│   │   ├── decorators.py # admin_required
│   │   ├── blueprints/   # auth, main, markets, trading, support, admin, api
│   │   ├── templates/    # Jinja pages
│   │   └── static/       # app.css, app.js, favicon.svg
│   ├── tests/            # pytest suite (40 tests)
│   └── instance/         # local SQLite DB (git-ignored, created at runtime)
```

---

## 2. Features implemented

**Client**
- Register / sign in / sign out with hashed passwords and CSRF-protected forms.
- Client dashboard: demo balance, positions value, total equity, watchlist, recent activity, market summary.
- Markets page: search by symbol/name, filter by asset class, 16 seeded instruments across
  stocks, crypto, forex, commodities and indices.
- Watchlist add/remove per user.
- Simulated buy/sell orders with validation, position tracking and an average-price model.
- One-time submission tokens on simulated orders and demo top-ups so a double-click cannot
  place the same order or add the same funds twice.
- Portfolio with holdings, cost basis and unrealised P/L.
- Transaction history (side, instrument, quantity, execution price, amount, status, timestamp).
- Demo top-up that adds **fictional** funds and records an auditable simulated transaction.
- Support centre: submit a request and track its status; requests are private to the user.

**Administrator**
- Server-enforced admin-only area (`/admin`).
- Platform statistics, user list (no secrets shown), all simulated transactions, support queue.
- Update support request status (open / in progress / resolved).

**Platform**
- Read-only JSON API (`/api/instruments`) for the static site to consume.
- Health endpoint (`/health`).
- Responsive dark UI reusing the VELTRIX design language; mobile navigation, empty/loading/error
  states, keyboard focus styles and reduced-motion support.

## 3. Features that are intentionally simulated / not implemented

- No real market data feed. Prices are **seeded, illustrative examples** and are labelled
  "Illustrative demo prices — not live market data."
- No real deposits, withdrawals, payment provider or card handling.
- No real order execution, custody, settlement or clearing.
- No real KYC/AML processing. No identity documents are collected.
- No real human support staff. The support queue is a demo workflow, not a staffed 24/7 service.
- No multi-currency conversion; demo cash is a single configured currency (USD by default).

## 4. Technology stack

- **Backend:** Python 3.11, Flask 3.1, Flask-SQLAlchemy 3.1, Flask-Login, Flask-WTF,
  WTForms, Werkzeug (scrypt password hashing), python-dotenv.
- **Database:** SQLite for local development (PostgreSQL-compatible SQLAlchemy models).
- **Tests:** pytest.
- **Frontend:** server-rendered Jinja templates + a small vanilla-JS enhancement file (no build step).
- **Static site:** plain HTML/CSS/JS (unchanged stack), deployable to GitHub Pages.

---

## 5. Local setup

```powershell
# 1. Go to the backend
cd backend

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Configure the environment (optional locally)
Copy-Item .env.example .env
#   Edit .env and set a strong SECRET_KEY.

# 5. Create the database and seed the demo instruments
python -m flask --app run seed

# 6. Run the development server
python run.py
#   -> http://127.0.0.1:5000
```

### Database location

- Default: `backend/instance/veltrix.db` (SQLite). The `instance/` folder and `*.db`
  files are excluded from version control.
- Override with the `DATABASE_URL` environment variable, e.g.
  `postgresql+psycopg://user:pass@host:5432/veltrix`.
- The app creates missing tables on start; `flask --app run seed` loads the demo instruments.

### Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Signs session cookies and CSRF tokens. **Required in production.** | insecure dev value + warning |
| `FLASK_ENV` | `development` / `testing` / `production` | `development` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///backend/instance/veltrix.db` |
| `SESSION_COOKIE_SECURE` | Set `1` to send cookies only over HTTPS (production) | `0` |
| `CORS_ORIGINS` | Comma-separated frontend origins allowed to call `/api/*` | empty |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Optional: bootstrap a dev admin during `seed` | empty |
| `ADMIN_NAME` | Display name for the seeded admin | `Veltrix Admin` |
| `DEMO_STARTING_BALANCE` | Fictional starting cash for a new demo account | `10000.00` |
| `HOST` / `PORT` | Bind address for `python run.py` | `127.0.0.1` / `5000` |

> Never commit a real `.env`. `.env` is git-ignored. No secrets are hard-coded.

### Creating an administrator

No predictable admin account is shipped. To create one for local development:

```powershell
$env:ADMIN_EMAIL="admin@yourdomain.example"
$env:ADMIN_PASSWORD="a-strong-unique-password"
python -m flask --app run seed
```

Admins can reach `/admin`. Ordinary clients receive **HTTP 403** on admin routes.

---

## 6. Running the tests

```powershell
cd backend
python -m pytest
```

**Actual result (this build):**

```
40 passed in ~22s
```

The suite covers: application startup, DB initialisation, registration, duplicate-email
handling, registration validation, successful/failed login, logout (and that sign-out clears
client access), client-route protection (including anonymous POSTs to `/trade` and the
watchlist), admin-route protection (403 for clients, redirect for anonymous), cross-user data
isolation, market search and filtering, watchlist add/remove, invalid/insufficient trade inputs,
buy/sell balance and position accounting, average price, transaction history, demo top-up,
replayed/invalid order-submission rejection, support request creation and isolation, admin status
updates, admin pages never exposing password hashes, CSRF rejection, the JSON API and the health
endpoint.

HTTP smoke test against a running server (`python run.py`):

```
GET /            -> 200
GET /markets/    -> 200
GET /login       -> 200
GET /health      -> {"status":"ok","database":"up","mode":"simulation"}
register -> dashboard -> simulated buy -> transaction history -> support request  (all OK)
GET /admin/ (as client) -> 403
```

---

## 7. Try the complete demo flow

1. Open `http://127.0.0.1:5000/` and click **Open a demo account**.
2. Register (any email; password ≥ 8 characters). You start with fictional demo funds.
3. On the **Dashboard**, review balance, watchlist and market summary.
4. Open **Markets**, search/filter, and add a couple of instruments to your watchlist.
5. Open an instrument and place a **simulated buy** (try a fractional quantity for e.g. `BTC/USD`).
6. Check **Portfolio** and **Activity** for updated balances and the transaction record.
7. Try to sell more than you own, or buy more than your demo cash allows — the order is rejected.
8. Use **Add demo funds** on the portfolio page (adds fictional funds only).
9. Submit a **Support request** and see its status.
10. As an admin (`/admin`), review users, transactions and support requests, and update a status.

---

## 8. GitHub Pages + backend deployment

GitHub Pages serves **static files only** — it cannot run Flask or host a persistent database.
The two parts deploy independently:

1. **Static concept site** stays on GitHub Pages (as it is today).
2. **Flask backend** is deployed as a separate service (Render, Railway, Fly.io, a VPS with
   gunicorn/waitress, etc.). This repository includes deployment helpers so the backend can be
   hosted on its own:

   - `backend/requirements-prod.txt` — adds `gunicorn`, `waitress` and the `psycopg` PostgreSQL
     driver on top of the runtime dependencies.
   - `backend/Procfile` — `web: gunicorn wsgi:app --bind 0.0.0.0:$PORT`.
   - `backend/render.yaml` — an example Render blueprint (web service + managed Postgres) with
     `SECRET_KEY` generated, `SESSION_COOKIE_SECURE=1` and a `/health` check.

   Start it with the WSGI entry point:

   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app      # Linux
   waitress-serve --port=8000 wsgi:app          # Windows
   ```

   Set `SECRET_KEY`, `SESSION_COOKIE_SECURE=1`, a production `DATABASE_URL` (e.g. Postgres
   because SQLite files do not persist reliably on every host) and `CORS_ORIGINS` to your
   Pages origin.

3. **Connect the frontend to the backend:** set the `veltrix-app-url` meta tag in
   `index.html` to the deployed backend URL, e.g.

   ```html
   <meta name="veltrix-app-url" content="https://veltrix-demo.onrender.com">
   ```

   When set, the "Log in", "Open an account" and dashboard buttons on the static site link to
   the live demo. When empty, the original in-page preview is used and the site keeps working
   exactly as before. The static site can also read demo prices from `GET /api/instruments`
   (narrow CORS is configured server-side via `CORS_ORIGINS`).

> The backend in this repository has **not** been deployed. It runs locally; deployment is the
> documented next step.

---

## 9. Security notes

- Passwords are hashed with Werkzeug's scrypt-based `generate_password_hash`; plaintext is
  never stored or logged.
- State-changing forms are CSRF-protected (Flask-WTF); missing/invalid tokens are rejected.
- Sessions use `HttpOnly`, `SameSite=Lax` cookies; `Secure` is enabled via config in production.
- All database access goes through the SQLAlchemy ORM (parameterised queries).
- Registration/login return generic errors to avoid account enumeration.
- Admin routes are authorised on the server (`admin_required`), not merely hidden in the UI.
- A per-user data boundary prevents reading another user's transactions or support requests.
- Simulated orders and demo top-ups carry a one-time submission token, so a replayed form
  (e.g. a double-click) is rejected without changing balances or positions.
- The admin UI never displays password hashes or other sensitive values.
- CORS for the JSON API is limited to explicitly configured origins and read-only (`GET`).

## 10. Known limitations

- SQLite is intended for local/demo use; production needs a server database (see §8).
- No email delivery: password recovery is not implemented (there is no recovery flow in the app).
- Prices are static seed values; there is no scheduler or live feed.
- No rate limiting on auth endpoints (recommended before any public deployment).
- No multi-currency support and no realised-P/L reporting.
- The static concept site's preview forms remain non-functional by design.

## 11. Recommended next steps

1. Deploy the backend (Postgres + gunicorn/waitress) and set `veltrix-app-url` on the Pages site.
2. Add rate limiting and login throttling (e.g. Flask-Limiter).
3. Add an audited, append-only ledger for transactions; separate "risk" review states.
4. Integrate a legitimate market-data provider for the `Instrument` prices (kept out of scope here).
5. Add email verification and a real password-recovery flow.
6. Expand admin tooling: user suspension, CSV export, audit log persistence.

---

## Brand

VELTRIX is a temporary placeholder name. Verify trademark, domain and company-name
availability before commercial use.

## Original concept disclaimer (retained)

This project began as a front-end concept with no backend, database, real authentication,
payment provider, identity verification service, live market feed or trade execution. Before any
real launch, engage qualified security and compliance professionals and implement
jurisdiction-appropriate licensing/compliance, secure authentication and MFA, backend
authorization, encrypted data handling, an audited transaction ledger, payment integrations,
KYC/AML workflows, support operations, monitoring, backups, disaster recovery and load testing.
