"""
地区、商圈、商店的API路由
"""
from typing import Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.crud_region import region, business_district, store
from app.models import (
    Message,
    Region, RegionCreate, RegionUpdate, RegionPublic, RegionsPublic,
    BusinessDistrict, BusinessDistrictCreate, BusinessDistrictUpdate, 
    BusinessDistrictPublic, BusinessDistrictsPublic,
    Store, StoreCreate, StoreUpdate, StorePublic, StoresPublic,
)

router = APIRouter()


# Region routes
@router.get("/regions/", response_model=RegionsPublic)
def read_regions(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> Any:
    """
    获取地区列表
    """
    count_statement = select(func.count()).select_from(Region)
    count = session.exec(count_statement).one()
    
    regions = region.get_multi(session=session, skip=skip, limit=limit)
    return RegionsPublic(data=regions, count=count)


@router.get("/regions/{region_id}", response_model=RegionPublic)
def read_region(session: SessionDep, region_id: uuid.UUID) -> Any:
    """
    根据ID获取地区
    """
    region_obj = region.get(session=session, id=region_id)
    if not region_obj:
        raise HTTPException(status_code=404, detail="地区不存在")
    return region_obj


@router.post("/regions/", response_model=RegionPublic)
def create_region(
    *, session: SessionDep, region_in: RegionCreate, current_user: CurrentUser
) -> Any:
    """
    创建新地区 (需要超级用户权限)
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="权限不足")
    
    # 检查编码是否已存在
    existing_region = region.get_by_code(session=session, code=region_in.code)
    if existing_region:
        raise HTTPException(status_code=400, detail="地区编码已存在")
    
    region_obj = region.create(session=session, obj_in=region_in)
    return region_obj


@router.put("/regions/{region_id}", response_model=RegionPublic)
def update_region(
    *,
    session: SessionDep,
    region_id: uuid.UUID,
    region_in: RegionUpdate,
    current_user: CurrentUser,
) -> Any:
    """
    更新地区 (需要超级用户权限)
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="权限不足")
    
    region_obj = region.get(session=session, id=region_id)
    if not region_obj:
        raise HTTPException(status_code=404, detail="地区不存在")
    
    region_obj = region.update(session=session, db_obj=region_obj, obj_in=region_in)
    return region_obj


@router.delete("/regions/{region_id}")
def delete_region(
    session: SessionDep, region_id: uuid.UUID, current_user: CurrentUser
) -> Message:
    """
    删除地区 (需要超级用户权限)
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="权限不足")
    
    region_obj = region.get(session=session, id=region_id)
    if not region_obj:
        raise HTTPException(status_code=404, detail="地区不存在")
    
    region.remove(session=session, id=region_id)
    return Message(message="地区删除成功")


# Business District routes
@router.get("/business-districts/", response_model=BusinessDistrictsPublic)
def read_business_districts(
    session: SessionDep, 
    region_id: uuid.UUID | None = None,
    skip: int = 0, 
    limit: int = 100
) -> Any:
    """
    获取商圈列表，可按地区筛选
    """
    if region_id:
        districts = business_district.get_by_region(
            session=session, region_id=region_id, skip=skip, limit=limit
        )
        count_statement = select(func.count()).select_from(BusinessDistrict).where(
            BusinessDistrict.region_id == region_id
        )
    else:
        districts = business_district.get_multi(session=session, skip=skip, limit=limit)
        count_statement = select(func.count()).select_from(BusinessDistrict)
    
    count = session.exec(count_statement).one()
    return BusinessDistrictsPublic(data=districts, count=count)


@router.get("/business-districts/search")
def search_business_districts(
    session: SessionDep, q: str, skip: int = 0, limit: int = 100
) -> BusinessDistrictsPublic:
    """
    搜索商圈
    """
    districts = business_district.search(
        session=session, query=q, skip=skip, limit=limit
    )
    return BusinessDistrictsPublic(data=districts, count=len(districts))


@router.get("/business-districts/{district_id}", response_model=BusinessDistrictPublic)
def read_business_district(session: SessionDep, district_id: uuid.UUID) -> Any:
    """
    根据ID获取商圈
    """
    district_obj = business_district.get(session=session, id=district_id)
    if not district_obj:
        raise HTTPException(status_code=404, detail="商圈不存在")
    return district_obj


@router.post("/business-districts/", response_model=BusinessDistrictPublic)
def create_business_district(
    *, session: SessionDep, district_in: BusinessDistrictCreate, current_user: CurrentUser
) -> Any:
    """
    创建新商圈 (需要超级用户权限)
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="权限不足")
    
    # 验证地区是否存在
    region_obj = region.get(session=session, id=district_in.region_id)
    if not region_obj:
        raise HTTPException(status_code=400, detail="指定的地区不存在")
    
    district_obj = business_district.create(session=session, obj_in=district_in)
    return district_obj


# Store routes
@router.get("/stores/", response_model=StoresPublic)
def read_stores(
    session: SessionDep,
    business_district_id: uuid.UUID | None = None,
    category: str | None = None,  # 支持: 全部, 优惠, 流量, 语音, 会员
    store_type: int | None = None,
    live_only: bool = False,
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
) -> Any:
    """
    获取商店列表，支持多种筛选条件
    支持的分类: 全部, 优惠, 流量, 语音, 会员
    """
    skip = page * limit

    # 构建查询条件 (这部分逻辑不变)
    query = select(Store)
    count_query = select(func.count()).select_from(Store)
    
    if business_district_id:
        query = query.where(Store.business_district_id == business_district_id)
        count_query = count_query.where(Store.business_district_id == business_district_id)
    
    if category and category != "全部":
        query = query.where(Store.category == category)
        count_query = count_query.where(Store.category == category)
    
    if store_type is not None:
        query = query.where(Store.type == store_type)
        count_query = count_query.where(Store.type == store_type)
    
    if live_only:
        query = query.where(Store.is_live == True)
        count_query = count_query.where(Store.is_live == True)
    
    # 获取总数
    total_count = session.exec(count_query).one()
    
    # 执行分页查询
    stores_list = session.exec(query.offset(skip).limit(limit)).all()
    
    is_more = page * limit < total_count
    
    return StoresPublic(data=stores_list, count=total_count, is_more=is_more)


@router.get("/stores/search")
def search_stores(
    session: SessionDep, q: str, skip: int = 0, limit: int = 20
) -> StoresPublic:
    """
    搜索商店
    """
    stores_list = store.search(session=session, query=q, skip=skip, limit=limit)
    
    # 获取搜索结果总数（简化处理，实际应该有专门的count搜索方法）
    total_count = len(stores_list) if len(stores_list) < limit else len(stores_list) + 1
    is_more = len(stores_list) == limit
    
    return StoresPublic(data=stores_list, count=total_count, is_more=is_more)


@router.get("/stores/{store_id}", response_model=StorePublic)
def read_store(session: SessionDep, store_id: uuid.UUID) -> Any:
    """
    根据ID获取商店
    """
    store_obj = store.get(session=session, id=store_id)
    if not store_obj:
        raise HTTPException(status_code=404, detail="商店不存在")
    return store_obj


@router.post("/stores/", response_model=StorePublic)
def create_store(
    *, session: SessionDep, store_in: StoreCreate, current_user: CurrentUser
) -> Any:
    """
    创建新商店 (需要超级用户权限)
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="权限不足")
    
    # 验证商圈是否存在
    district_obj = business_district.get(session=session, id=store_in.business_district_id)
    if not district_obj:
        raise HTTPException(status_code=400, detail="指定的商圈不存在")
    
    store_obj = store.create(session=session, obj_in=store_in)
    return store_obj


@router.put("/stores/{store_id}", response_model=StorePublic)
def update_store(
    *,
    session: SessionDep,
    store_id: uuid.UUID,
    store_in: StoreUpdate,
    current_user: CurrentUser,
) -> Any:
    """
    更新商店 (需要超级用户权限)
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="权限不足")
    
    store_obj = store.get(session=session, id=store_id)
    if not store_obj:
        raise HTTPException(status_code=404, detail="商店不存在")
    
    store_obj = store.update(session=session, db_obj=store_obj, obj_in=store_in)
    return store_obj


@router.delete("/stores/{store_id}")
def delete_store(
    session: SessionDep, store_id: uuid.UUID, current_user: CurrentUser
) -> Message:
    """
    删除商店 (需要超级用户权限)
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="权限不足")
    
    store_obj = store.get(session=session, id=store_id)
    if not store_obj:
        raise HTTPException(status_code=404, detail="商店不存在")
    
    store.remove(session=session, id=store_id)
    return Message(message="商店删除成功")