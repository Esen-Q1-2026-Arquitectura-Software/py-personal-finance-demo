import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AccountType(str, enum.Enum):
    checking = "checking"
    savings = "savings"
    credit = "credit"
    investment = "investment"


class CategoryType(str, enum.Enum):
    income = "income"
    expense = "expense"


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"
    transfer = "transfer"


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    type: Mapped[CategoryType] = mapped_column(Enum(CategoryType), nullable=False)

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="category"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped["Account"] = relationship("Account", back_populates="transactions")
    category: Mapped["Category | None"] = relationship(
        "Category", back_populates="transactions"
    )
