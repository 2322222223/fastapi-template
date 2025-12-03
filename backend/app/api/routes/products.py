from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select, func

from app import crud_product
from app import crud_product_detail
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.models import (
    Product,
    ProductCreate,
    ProductPublic,
    ProductsPublic,
    ProductUpdate,
    ProductDetail,
    ProductDetailPublic,
    User,
)

router = APIRouter()


@router.get("/", response_model=ProductsPublic)
def read_products(
    *,
    session: SessionDep,
    store_id: UUID | None = None,
    category: str | None = None,
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
) -> Any:
    """
    获取商品列表，支持按店铺和分类筛选
    """
    skip = page * limit
    
    # 构建查询条件
    query = select(Product)
    count_query = select(func.count()).select_from(Product)
    
    if store_id:
        query = query.where(Product.store_id == store_id)
        count_query = count_query.where(Product.store_id == store_id)
    
    if category:
        query = query.where(Product.category == category)
        count_query = count_query.where(Product.category == category)
    
    # 获取总数
    total_count = session.exec(count_query).one()
    
    # 执行分页查询
    products_list = session.exec(query.offset(skip).limit(limit)).all()
    
    is_more = page * limit < total_count
    
    return ProductsPublic(data=products_list, count=total_count, is_more=is_more)


@router.get("/store/{store_id}", response_model=ProductsPublic)
def read_products_by_store(
    *,
    session: SessionDep,
    store_id: UUID,
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
) -> Any:
    """
    获取指定店铺的商品列表
    """
    skip = page * limit
    
    # 获取总数
    total_count = crud_product.get_products_count(session, store_id=store_id)
    
    # 执行分页查询
    products_list = crud_product.get_products_by_store(
        session, store_id=store_id, skip=skip, limit=limit
    )
    
    is_more = page * limit < total_count
    
    return ProductsPublic(data=products_list, count=total_count, is_more=is_more)


@router.get("/{product_id}", response_model=ProductPublic)
def read_product(session: SessionDep, product_id: UUID) -> Any:
    """
    根据ID获取商品基础信息
    """
    product = crud_product.get_product(session, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.get("/{product_id}/detail", response_model=ProductDetailPublic)
def read_product_detail(session: SessionDep, product_id: UUID) -> Any:
    """
    根据商品ID获取商品详情
    """
    # 先检查商品是否存在
    product = crud_product.get_product(session, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    
    # 获取商品详情
    product_detail = crud_product_detail.get_product_detail_by_product_id(session, product_id=product_id)
    if not product_detail:
        raise HTTPException(status_code=404, detail="商品详情不存在")
    
    # 创建包含store_id的响应对象
    detail_data = product_detail.dict()
    detail_data['store_id'] = product.store_id
    
    return ProductDetailPublic(**detail_data)


@router.post("/", response_model=ProductPublic, dependencies=[Depends(get_current_active_superuser)])
def create_product(
    *,
    session: SessionDep,
    product_in: ProductCreate,
) -> Any:
    """
    创建新商品 (需要超级用户权限)
    """
    product = crud_product.create_product(session, obj_in=product_in)
    return product


@router.put("/{product_id}", response_model=ProductPublic, dependencies=[Depends(get_current_active_superuser)])
def update_product(
    *,
    session: SessionDep,
    product_id: UUID,
    product_in: ProductUpdate,
) -> Any:
    """
    更新商品信息 (需要超级用户权限)
    """
    product = crud_product.get_product(session, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product = crud_product.update_product(session, db_obj=product, obj_in=product_in)
    return product


@router.delete("/{product_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_product(
    *,
    session: SessionDep,
    product_id: UUID,
) -> Any:
    """
    删除商品 (需要超级用户权限)
    """
    product = crud_product.get_product(session, id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    crud_product.delete_product(session, id=product_id)
    return {"message": "商品已删除"}


@router.get("/search/", response_model=ProductsPublic)
def search_products(
    *,
    session: SessionDep,
    q: str = Query(..., description="搜索关键词"),
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
) -> Any:
    """
    搜索商品
    """
    skip = page * limit
    
    # 执行搜索
    products_list = crud_product.search_products(
        session, query=q, skip=skip, limit=limit
    )
    
    # 简化处理，实际应该有专门的count搜索方法
    total_count = len(products_list) if len(products_list) < limit else len(products_list) + 1
    is_more = len(products_list) == limit
    
    return ProductsPublic(data=products_list, count=total_count, is_more=is_more)
