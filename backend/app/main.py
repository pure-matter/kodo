from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import SessionLocal
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
from .seed import seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on every server start: applies any pending Alembic migrations,
    then seeds default categories/rules/allocations if the db is empty.
    This is a single-user local app with one process and no deploy step,
    so there's no reason to make "did you remember to migrate?" a thing
    the user has to think about."""
    alembic_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    with SessionLocal() as db:
        seed_all(db)
    yield


app = FastAPI(title="Kodo Personal Finance API", lifespan=lifespan)

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """An unhandled exception (as opposed to a raised HTTPException) skips
    Starlette's normal exception-handling path and reaches ServerErrorMiddleware
    directly, which doesn't run CORSMiddleware - the browser then sees a
    response with no CORS headers and reports a generic "Failed to fetch"
    instead of the actual error. Registering a handler here keeps the
    response inside the normal middleware stack so the real error reaches
    the frontend instead of being masked as a network failure."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})
