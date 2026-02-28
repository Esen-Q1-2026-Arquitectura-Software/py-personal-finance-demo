from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .models import AccountType, CategoryType, TransactionType

# ---------------------------------------------------------------------------
# Account schemas
# ---------------------------------------------------------------------------


class AccountBase(BaseModel):
    name: str
    type: AccountType
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = None
    type: AccountType | None = None
    balance: Decimal | None = None


class AccountRead(AccountBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Category schemas
# ---------------------------------------------------------------------------


class CategoryBase(BaseModel):
    name: str
    type: CategoryType


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    type: CategoryType | None = None


class CategoryRead(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Transaction schemas
# ---------------------------------------------------------------------------


class TransactionBase(BaseModel):
    account_id: int
    category_id: int | None = None
    amount: Decimal = Field(gt=0)
    description: str | None = None
    type: TransactionType
    date: datetime = Field(default_factory=datetime.utcnow)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    account_id: int | None = None
    category_id: int | None = None
    amount: Decimal | None = None
    description: str | None = None
    type: TransactionType | None = None
    date: datetime | None = None


class TransactionRead(TransactionBase):
    id: int
    created_at: datetime
    category: CategoryRead | None = None

    model_config = ConfigDict(from_attributes=True)
