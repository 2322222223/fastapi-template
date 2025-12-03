from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select, func

from app.models import Product, ProductCreate, ProductUpdate


def create_product(db: Session, *, obj_in: ProductCreate) -> Product:
    db_obj = Product.from_orm(obj_in)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_product(db: Session, id: UUID) -> Optional[Product]:
    return db.exec(select(Product).where(Product.id == id)).first()


def get_products_by_store(
    db: Session, *, store_id: UUID, skip: int = 0, limit: int = 100
) -> List[Product]:
    return db.exec(
        select(Product)
        .where(Product.store_id == store_id)
        .offset(skip)
        .limit(limit)
    ).all()


def get_products(
    db: Session, *, skip: int = 0, limit: int = 100, store_id: Optional[UUID] = None
) -> List[Product]:
    query = select(Product)
    if store_id:
        query = query.where(Product.store_id == store_id)
    return db.exec(query.offset(skip).limit(limit)).all()


def get_products_count(
    db: Session, *, store_id: Optional[UUID] = None
) -> int:
    query = select(func.count()).select_from(Product)
    if store_id:
        query = query.where(Product.store_id == store_id)
    return db.exec(query).one()


def update_product(
    db: Session, *, db_obj: Product, obj_in: ProductUpdate
) -> Product:
    update_data = obj_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_product(db: Session, *, id: UUID) -> Product:
    obj = db.exec(select(Product).where(Product.id == id)).first()
    db.delete(obj)
    db.commit()
    return obj


def search_products(
    db: Session, *, query: str, skip: int = 0, limit: int = 100
) -> List[Product]:
    return db.exec(
        select(Product)
        .where(
            (Product.title.contains(query)) |
            (Product.subtitle.contains(query)) |
            (Product.category.contains(query))
        )
        .offset(skip)
        .limit(limit)
    ).all()
