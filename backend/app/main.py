from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    accounts,
    categories,
    category_rules,
    imports,
    net_worth,
    reports,
    savings,
    transactions,
)

app = FastAPI(title="Kodo Personal Finance API")

# Local dev only: this app runs on localhost for a single user, with the
# React dev server on a different port (typically 5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(category_rules.router)
app.include_router(transactions.router)
app.include_router(imports.router)
app.include_router(savings.router)
app.include_router(net_worth.router)
app.include_router(reports.router)


@app.get("/health")
def health():
    return {"status": "ok"}
