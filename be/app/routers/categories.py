from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Category
from ..schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryRead])
def list_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Category).offset(skip).limit(limit).all()


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    return category


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{payload.name}' already exists",
        )
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    db.delete(category)
    db.commit()
