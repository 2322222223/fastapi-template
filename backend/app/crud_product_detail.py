from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select, func

from app.models import ProductDetail, ProductDetailCreate, ProductDetailUpdate


def create_product_detail(db: Session, *, obj_in: ProductDetailCreate) -> ProductDetail:
    db_obj = ProductDetail.model_validate(obj_in)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_product_detail(db: Session, id: UUID) -> Optional[ProductDetail]:
    return db.exec(select(ProductDetail).where(ProductDetail.id == id)).first()


def get_product_detail_by_product_id(db: Session, product_id: UUID) -> Optional[ProductDetail]:
    return db.exec(select(ProductDetail).where(ProductDetail.product_id == product_id)).first()


def get_product_details(
    db: Session, *, skip: int = 0, limit: int = 100
) -> List[ProductDetail]:
    return db.exec(select(ProductDetail).offset(skip).limit(limit)).all()


def get_product_details_count(db: Session) -> int:
    return db.exec(select(func.count(ProductDetail.id))).one()


def update_product_detail(
    db: Session, *, db_obj: ProductDetail, obj_in: ProductDetailUpdate
) -> ProductDetail:
    update_data = obj_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_product_detail(db: Session, *, id: UUID) -> ProductDetail:
    obj = db.exec(select(ProductDetail).where(ProductDetail.id == id)).first()
    db.delete(obj)
    db.commit()
    return obj


def search_product_details(
    db: Session, *, query: str, skip: int = 0, limit: int = 100
) -> List[ProductDetail]:
    return db.exec(
        select(ProductDetail)
        .where(
            (ProductDetail.name.contains(query)) |
            (ProductDetail.description.contains(query)) |
            (ProductDetail.tags.contains(query))
        )
        .offset(skip)
        .limit(limit)
    ).all()
