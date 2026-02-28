from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine
from .models import Category  # noqa: F401 – needed so Base knows about models
from .models import Account, Transaction  # noqa: F401
from .routers import accounts, categories, transactions

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables (idempotent – does nothing if they already exist)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed_categories(db)
    finally:
        db.close()

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
