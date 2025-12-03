"""
地区、商圈、商店的CRUD操作
"""
from typing import Any
import uuid
from sqlmodel import Session, select, func, or_
from app.models import (
    Region, RegionCreate, RegionUpdate,
    BusinessDistrict, BusinessDistrictCreate, BusinessDistrictUpdate,
    Store, StoreCreate, StoreUpdate
)


class CRUDRegion:
    def create(self, *, session: Session, obj_in: RegionCreate) -> Region:
        """创建地区"""
        db_obj = Region.model_validate(obj_in)
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj
    
    def get(self, session: Session, id: uuid.UUID) -> Region | None:
        """根据ID获取地区"""
        return session.get(Region, id)
    
    def get_by_code(self, session: Session, code: str) -> Region | None:
        """根据编码获取地区"""
        statement = select(Region).where(Region.code == code)
        return session.exec(statement).first()
    
    def get_multi(
        self, session: Session, *, skip: int = 0, limit: int = 100
    ) -> list[Region]:
        """获取地区列表"""
        statement = select(Region).offset(skip).limit(limit)
        return session.exec(statement).all()
    
    def update(
        self, *, session: Session, db_obj: Region, obj_in: RegionUpdate
    ) -> Region:
        """更新地区"""
        obj_data = obj_in.model_dump(exclude_unset=True)
        db_obj.sqlmodel_update(obj_data)
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj
    
    def remove(self, *, session: Session, id: uuid.UUID) -> Region:
        """删除地区"""
        obj = session.get(Region, id)
        session.delete(obj)
        session.commit()
        return obj


class CRUDBusinessDistrict:
    def create(
        self, *, session: Session, obj_in: BusinessDistrictCreate
    ) -> BusinessDistrict:
        """创建商圈"""
        db_obj = BusinessDistrict.model_validate(obj_in)
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj
    
    def get(self, session: Session, id: uuid.UUID) -> BusinessDistrict | None:
        """根据ID获取商圈"""
        return session.get(BusinessDistrict, id)
    
    def get_multi(
        self, session: Session, *, skip: int = 0, limit: int = 100
    ) -> list[BusinessDistrict]:
        """获取商圈列表"""
        statement = select(BusinessDistrict).offset(skip).limit(limit)
        return session.exec(statement).all()
    
    def get_by_region(
        self, session: Session, region_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> list[BusinessDistrict]:
        """根据地区获取商圈列表"""
        statement = (
            select(BusinessDistrict)
            .where(BusinessDistrict.region_id == region_id)
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    def search(
        self, session: Session, *, query: str, skip: int = 0, limit: int = 100
    ) -> list[BusinessDistrict]:
        """搜索商圈"""
        statement = (
            select(BusinessDistrict)
            .where(
                or_(
                    BusinessDistrict.name.contains(query),
                    BusinessDistrict.address.contains(query)
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    def update(
        self, *, session: Session, db_obj: BusinessDistrict, obj_in: BusinessDistrictUpdate
    ) -> BusinessDistrict:
        """更新商圈"""
        obj_data = obj_in.model_dump(exclude_unset=True)
        db_obj.sqlmodel_update(obj_data)
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj
    
    def remove(self, *, session: Session, id: uuid.UUID) -> BusinessDistrict:
        """删除商圈"""
        obj = session.get(BusinessDistrict, id)
        session.delete(obj)
        session.commit()
        return obj


class CRUDStore:
    def create(self, *, session: Session, obj_in: StoreCreate) -> Store:
        """创建商店"""
        db_obj = Store.model_validate(obj_in)
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj
    
    def get(self, session: Session, id: uuid.UUID) -> Store | None:
        """根据ID获取商店"""
        return session.get(Store, id)
    
    def get_multi(
        self, session: Session, *, skip: int = 0, limit: int = 100
    ) -> list[Store]:
        """获取商店列表"""
        statement = select(Store).offset(skip).limit(limit)
        return session.exec(statement).all()
    
    def get_by_business_district(
        self,
        session: Session,
        business_district_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> list[Store]:
        """根据商圈获取商店列表"""
        statement = (
            select(Store)
            .where(Store.business_district_id == business_district_id)
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    def get_by_category(
        self,
        session: Session,
        category: str,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> list[Store]:
        """根据分类获取商店列表"""
        statement = (
            select(Store)
            .where(Store.category == category)
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    def search(
        self, session: Session, *, query: str, skip: int = 0, limit: int = 100
    ) -> list[Store]:
        """搜索商店"""
        statement = (
            select(Store)
            .where(
                or_(
                    Store.name.contains(query),
                    Store.category.contains(query),
                    Store.tags.contains(query)
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    def get_by_type(
        self,
        session: Session,
        store_type: int,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> list[Store]:
        """根据类型获取商店列表"""
        statement = (
            select(Store)
            .where(Store.type == store_type)
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    def get_live_stores(
        self, session: Session, *, skip: int = 0, limit: int = 100
    ) -> list[Store]:
        """获取营业中的商店列表"""
        statement = (
            select(Store)
            .where(Store.is_live == True)
            .offset(skip)
            .limit(limit)
        )
        return session.exec(statement).all()
    
    def update(
        self, *, session: Session, db_obj: Store, obj_in: StoreUpdate
    ) -> Store:
        """更新商店"""
        obj_data = obj_in.model_dump(exclude_unset=True)
        db_obj.sqlmodel_update(obj_data)
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj
    
    def remove(self, *, session: Session, id: uuid.UUID) -> Store:
        """删除商店"""
        obj = session.get(Store, id)
        session.delete(obj)
        session.commit()
        return obj


# 创建CRUD实例
region = CRUDRegion()
business_district = CRUDBusinessDistrict()
store = CRUDStore()