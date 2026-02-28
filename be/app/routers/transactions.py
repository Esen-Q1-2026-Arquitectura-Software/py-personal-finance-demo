from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Account, Transaction
from ..schemas import TransactionCreate, TransactionRead, TransactionUpdate
from ..websocket import manager

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _get_or_404(transaction_id: int, db: Session) -> Transaction:
    txn = (
        db.query(Transaction)
        .options(joinedload(Transaction.category))
        .filter(Transaction.id == transaction_id)
        .first()
    )
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    return txn


@router.get("/", response_model=list[TransactionRead])
def list_transactions(
    skip: int = 0,
    limit: int = 100,
    account_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Transaction).options(joinedload(Transaction.category))
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    return query.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    return _get_or_404(transaction_id, db)


@router.post("/", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    # Validate that the referenced account exists
    account = db.query(Account).filter(Account.id == payload.account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id={payload.account_id} not found",
        )

    txn = Transaction(**payload.model_dump())
    db.add(txn)

    # Update account balance
    if payload.type == "income":
        account.balance += payload.amount
    elif payload.type == "expense":
        account.balance -= payload.amount

    db.commit()
    db.refresh(txn)
    manager.notify(
        {
            "event": "transaction_created",
            "message": f"New {payload.type} of ${float(payload.amount):.2f} added.",
            "alert": "success",
        }
    )
    return _get_or_404(txn.id, db)


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int, payload: TransactionUpdate, db: Session = Depends(get_db)
):
    txn = _get_or_404(transaction_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(txn, field, value)
    db.commit()
    db.refresh(txn)
    manager.notify(
        {
            "event": "transaction_updated",
            "message": f"Transaction #{transaction_id} updated.",
            "alert": "info",
        }
    )
    return _get_or_404(transaction_id, db)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    txn = _get_or_404(transaction_id, db)
    db.delete(txn)
    db.commit()
    manager.notify(
        {
            "event": "transaction_deleted",
            "message": "Transaction deleted.",
            "alert": "warning",
        }
    )
