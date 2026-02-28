import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from starlette.websockets import WebSocketDisconnect

from .database import Base, SessionLocal, engine
from .models import Category  # noqa: F401 – needed so Base knows about models
from .models import Account, Transaction  # noqa: F401
from .routers import accounts, categories, transactions
from .websocket import manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed default categories if the table is empty
# ---------------------------------------------------------------------------

DEFAULT_CATEGORIES = [
    ("Salary", "income"),
    ("Freelance", "income"),
    ("Investments", "income"),
    ("Other Income", "income"),
    ("Housing", "expense"),
    ("Groceries", "expense"),
    ("Transport", "expense"),
    ("Utilities", "expense"),
    ("Healthcare", "expense"),
    ("Entertainment", "expense"),
    ("Dining Out", "expense"),
    ("Education", "expense"),
    ("Clothing", "expense"),
    ("Other Expense", "expense"),
]


def _seed_categories(db):
    if db.query(Category).count() == 0:
        for name, ctype in DEFAULT_CATEGORIES:
            db.add(Category(name=name, type=ctype))
        db.commit()


# ---------------------------------------------------------------------------
# Lifespan: runs once at startup and once at shutdown
# Reference: https://fastapi.tiangolo.com/advanced/events/
# ---------------------------------------------------------------------------


def _wait_for_db(retries: int = 30, delay: float = 2.0) -> None:
    """Block until the database is reachable, retrying on failure."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database is ready (attempt %d).", attempt)
            return
        except OperationalError as exc:
            logger.warning(
                "Database not ready (attempt %d/%d): %s", attempt, retries, exc
            )
            if attempt == retries:
                raise RuntimeError(
                    f"Could not connect to the database after {retries} attempts."
                ) from exc
            time.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wait until MySQL accepts connections before touching the schema
    _wait_for_db()

    # Create all tables (idempotent – does nothing if they already exist)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed_categories(db)
    finally:
        db.close()

    # Bind the asyncio event loop so sync routers can schedule WS broadcasts
    manager.set_event_loop(asyncio.get_running_loop())

    yield  # application is running


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Personal Finance API",
    version="1.0.0",
    description="FastAPI backend for the personal finance demo application.",
    lifespan=lifespan,
)

# Allow the Flask frontend (running on port 5000) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://frontend:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open; ignore any client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
