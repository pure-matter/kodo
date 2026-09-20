# Kodo

A personal finance tracker: import bank/credit card statements, auto-categorize spending, track budgets, savings goals, and net worth. Runs entirely on localhost — no hosting, no external accounts.

## Database

The database is **SQLite** — a single file (`backend/kodo.db`), not a separate server process. There's nothing to start, stop, or configure beyond the file itself.

- **Schema changes** are managed by Alembic migrations (`backend/alembic/versions/`), applied **automatically every time the backend starts** — no manual step needed, even after pulling new code with a new migration.
- **Seed data** (categories, budgets, savings allocations, starter rules) comes from `backend/app/seed.py`, also run automatically on startup. It's idempotent — only fills in what's missing, never duplicates rows.
- **Backup**: just copy `backend/kodo.db` somewhere.
- **Start fresh**: stop the backend, delete `backend/kodo.db`, start it again — it'll recreate and reseed itself.
- **Inspect it directly**: `sqlite3 backend/kodo.db` (CLI), or open it in a GUI tool like [DB Browser for SQLite](https://sqlitebrowser.org/) if you want to poke at tables by hand.

## Running it

Requires Python 3.11+ and Node 18+.

**Backend** (from `backend/`):
```bash
python3 -m venv .venv && source .venv/bin/activate   # first time only
pip install -r requirements-dev.txt                   # first time, or after pulling new deps
uvicorn app.main:app --reload
```
Migrations and seeding happen automatically on startup — nothing else to run. Runs at `http://localhost:8000` (interactive API docs at `/docs`).

**Frontend** (from `frontend/`, in a separate terminal):
```bash
npm install       # first time, or after pulling new deps
npm run dev
```
Runs at `http://localhost:5173` — open that in your browser.

**Tests**: `cd backend && python3 -m pytest` / `cd frontend && npm test`

## User guide

**Accounts** — Add each bank account/card. If it has a supported parser (BoA checking/savings, BoA credit card, Amex), you can upload statement files there; otherwise it's a manual-entry account (e.g. GTBank). Click **manage** on any account row to log a balance (feeds Net Worth) or, for manual accounts, add a transaction by hand.

**Transactions** — Every imported transaction is auto-categorized where a rule matches; the rest show as "Uncategorized." Change a category via the dropdown. Click **"always categorize like this?"** to teach the app a rule from that transaction's exact text, so future imports of the same merchant categorize automatically — the match text is editable, since bank statements sometimes truncate merchant names oddly.

**Categories** — Add, rename, rebudget, or delete categories and rules (a category with existing transactions can't be deleted until they're reassigned). The spend chart toggles between **by category** and **by bucket** (Needs/Wants/Savings, where Savings pulls from your savings allocations, not a category group). **Archive a month** saves each category's total for that month, then permanently deletes the underlying transactions — the history chart still shows archived months afterward, but re-importing a statement for an archived month may create duplicates, since the records used to detect them are gone. Nothing is archived automatically; you choose when.

**Dashboard** — Net worth (from your logged balances), spend vs. budget per category (green/amber/red), and savings progress toward each monthly allocation target.

**Re-importing a file** is safe — already-imported transactions are skipped, not duplicated.
