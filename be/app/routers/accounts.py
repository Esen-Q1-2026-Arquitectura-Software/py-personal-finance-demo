from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account
from ..schemas import AccountCreate, AccountRead, AccountUpdate
from ..websocket import manager

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("/", response_model=list[AccountRead])
def list_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Account).offset(skip).limit(limit).all()


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    return account


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    account = Account(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    manager.notify(
        {
            "event": "account_created",
            "message": f"Account '{account.name}' created.",
            "alert": "success",
        }
    )
    return account


@router.put("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    manager.notify(
        {
            "event": "account_updated",
            "message": f"Account '{account.name}' updated.",
            "alert": "info",
        }
    )
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    name = account.name
    db.delete(account)
    db.commit()
    manager.notify(
        {
            "event": "account_deleted",
            "message": f"Account '{name}' deleted.",
            "alert": "warning",
        }
    )
