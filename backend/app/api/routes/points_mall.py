"""
积分商城API路由
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_db, get_current_user
from app.models import (
    User,
    PointsProductCategoryCreate,
    PointsProductCategoryUpdate,
    PointsProductCategoryPublic,
    PointsProductCategoriesPublic,
    PointsProductCreate,
    PointsProductUpdate,
    PointsProductPublic,
    PointsProductExchangeUpdate,
    PointsProductExchangePublic,
    PointsProductsPublic,
    PointsProductHotProductsPublic,
    PointsProductExchangesPublic,
    PointsProductCategoryType,
    PointsProductLabel,
    ExchangeStatus,
    PointsRedemptionLeaderboardPublic,
    ProductExchangeLeaderboardPublic
)
from app.crud_points_mall import (
    # 分类相关
    create_points_product_category,
    get_points_product_category,
    get_points_product_categories,
    update_points_product_category,
    delete_points_product_category,
    # 商品相关
    create_points_product,
    get_points_product,
    get_points_products,
    update_points_product,
    delete_points_product,
    get_hot_exchange_products,
    # 兑换相关
    exchange_points_product,
    get_points_product_exchange,
    get_user_exchanges,
    update_exchange_status,
    get_points_redemption_leaderboard,
    get_product_exchange_leaderboard
)

router = APIRouter()


# ==================== 分类相关接口 ====================

@router.post("/categories/", response_model=PointsProductCategoryPublic)
def create_category_endpoint(
    category_data: PointsProductCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建积分商品分类（管理员）"""
    try:
        category = create_points_product_category(db, category_data)
        return category
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建分类失败：{str(e)}")


@router.get("/categories/", response_model=PointsProductCategoriesPublic)
def get_categories_endpoint(
    category_type: Optional[PointsProductCategoryType] = Query(None, description="分类类型"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    db: Session = Depends(get_db)
):
    """获取分类列表"""
    try:
        categories, _ = get_points_product_categories(
            db,
            category_type=category_type,
            is_active=is_active,
            skip=0,
            limit=100
        )
        return PointsProductCategoriesPublic(data=categories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类列表失败：{str(e)}")


@router.get("/categories/{category_id}", response_model=PointsProductCategoryPublic)
def get_category_endpoint(
    category_id: UUID,
    db: Session = Depends(get_db)
):
    """根据ID获取分类"""
    try:
        category = get_points_product_category(db, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        return category
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类失败：{str(e)}")


@router.put("/categories/{category_id}", response_model=PointsProductCategoryPublic)
def update_category_endpoint(
    category_id: UUID,
    category_data: PointsProductCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新分类（管理员）"""
    try:
        category = update_points_product_category(db, category_id, category_data)
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        return category
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新分类失败：{str(e)}")


@router.delete("/categories/{category_id}")
def delete_category_endpoint(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除分类（管理员）"""
    try:
        success = delete_points_product_category(db, category_id)
        if not success:
            raise HTTPException(status_code=404, detail="分类不存在")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"删除分类失败：{str(e)}")


# ==================== 商品相关接口 ====================

@router.post("/products/", response_model=PointsProductPublic)
def create_product_endpoint(
    product_data: PointsProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建积分商品（管理员）"""
    try:
        product = create_points_product(db, product_data)
        return product
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建商品失败：{str(e)}")


@router.get("/products/", response_model=PointsProductsPublic)
def get_products_endpoint(
    category_id: Optional[UUID] = Query(None, description="分类ID"),
    category_type: Optional[PointsProductCategoryType] = Query(None, description="分类类型"),
    is_active: Optional[bool] = Query(None, description="是否上架"),
    page: int = Query(0, ge=0, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取商品列表"""
    try:
        skip = page * page_size
        products, total = get_points_products(
            db,
            category_id=category_id,
            category_type=category_type,
            is_active=is_active,
            skip=skip,
            limit=page_size
        )
        
        return PointsProductsPublic(
            data=products,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取商品列表失败：{str(e)}")


@router.get("/products/hot", response_model=PointsProductHotProductsPublic)
def get_hot_products_endpoint(
    limit: int = Query(4, ge=1, le=20, description="返回数量，默认4条"),
    db: Session = Depends(get_db)
):
    """获取热门兑换商品列表"""
    try:
        products = get_hot_exchange_products(db, limit=limit)
        return PointsProductHotProductsPublic(data=products)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热门商品失败：{str(e)}")


@router.get("/products/{product_id}", response_model=PointsProductPublic)
def get_product_endpoint(
    product_id: UUID,
    db: Session = Depends(get_db)
):
    """根据ID获取商品详情"""
    try:
        product = get_points_product(db, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        
        # 获取分类信息
        from app.crud_points_mall import get_points_product_category
        category = get_points_product_category(db, product.category_id)
        
        product_public = PointsProductPublic.model_validate(product)
        product_public.category_name = category.name if category else None
        
        return product_public
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取商品失败：{str(e)}")


@router.put("/products/{product_id}", response_model=PointsProductPublic)
def update_product_endpoint(
    product_id: UUID,
    product_data: PointsProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新商品（管理员）"""
    try:
        product = update_points_product(db, product_id, product_data)
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
        
        # 获取分类信息
        from app.crud_points_mall import get_points_product_category
        category = get_points_product_category(db, product.category_id)
        
        product_public = PointsProductPublic.model_validate(product)
        product_public.category_name = category.name if category else None
        
        return product_public
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新商品失败：{str(e)}")


@router.delete("/products/{product_id}")
def delete_product_endpoint(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除商品（管理员）"""
    try:
        success = delete_points_product(db, product_id)
        if not success:
            raise HTTPException(status_code=404, detail="商品不存在")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"删除商品失败：{str(e)}")


# ==================== 兑换相关接口 ====================

@router.post("/products/{product_id}/exchange", response_model=PointsProductExchangePublic)
def exchange_product_endpoint(
    product_id: UUID,
    quantity: int = Query(1, ge=1, description="兑换数量"),
    recipient_info: Optional[str] = Query(None, description="收货信息（JSON字符串，实物商品需要）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """兑换积分商品"""
    try:
        exchange, message = exchange_points_product(
            db,
            current_user.id,
            product_id,
            quantity=quantity,
            recipient_info=recipient_info
        )
        
        if not exchange:
            raise HTTPException(status_code=400, detail=message)
        
        # 获取商品信息
        product = get_points_product(db, product_id)
        
        exchange_public = PointsProductExchangePublic.model_validate(exchange)
        exchange_public.product_name = product.name if product else None
        exchange_public.product_image_url = product.image_url if product else None
        # 解析 tags 字段（逗号分隔的字符串）为列表
        if product and product.tags:
            exchange_public.tags = [tag.strip() for tag in product.tags.split(",") if tag.strip()]
        else:
            exchange_public.tags = []
        
        return exchange_public
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"兑换失败：{str(e)}")


@router.get("/exchanges/", response_model=PointsProductExchangesPublic)
def get_my_exchanges_endpoint(
    status: Optional[ExchangeStatus] = Query(None, description="兑换状态"),
    page: int = Query(0, ge=0, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的兑换记录"""
    try:
        skip = page * page_size
        exchanges, total = get_user_exchanges(
            db,
            current_user.id,
            status=status,
            skip=skip,
            limit=page_size
        )
        
        # 填充商品信息
        exchanges_public = []
        for exchange in exchanges:
            product = get_points_product(db, exchange.product_id)
            
            exchange_public = PointsProductExchangePublic.model_validate(exchange)
            exchange_public.product_name = product.name if product else None
            exchange_public.product_image_url = product.image_url if product else None
            # 解析 tags 字段（逗号分隔的字符串）为列表
            if product and product.tags:
                exchange_public.tags = [tag.strip() for tag in product.tags.split(",") if tag.strip()]
            else:
                exchange_public.tags = []
            
            exchanges_public.append(exchange_public)
        
        return PointsProductExchangesPublic(
            data=exchanges_public,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取兑换记录失败：{str(e)}")


@router.get("/exchanges/{exchange_id}", response_model=PointsProductExchangePublic)
def get_exchange_endpoint(
    exchange_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据ID获取兑换记录"""
    try:
        exchange = get_points_product_exchange(db, exchange_id, current_user.id)
        if not exchange:
            raise HTTPException(status_code=404, detail="兑换记录不存在或无权限访问")
        
        # 获取商品信息
        product = get_points_product(db, exchange.product_id)
        
        exchange_public = PointsProductExchangePublic.model_validate(exchange)
        exchange_public.product_name = product.name if product else None
        exchange_public.product_image_url = product.image_url if product else None
        # 解析 tags 字段（逗号分隔的字符串）为列表
        if product and product.tags:
            exchange_public.tags = [tag.strip() for tag in product.tags.split(",") if tag.strip()]
        else:
            exchange_public.tags = []
        
        return exchange_public
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取兑换记录失败：{str(e)}")


@router.put("/exchanges/{exchange_id}/status", response_model=PointsProductExchangePublic)
def update_exchange_status_endpoint(
    exchange_id: UUID,
    status: ExchangeStatus,
    exchange_code: Optional[str] = Query(None, description="兑换码"),
    notes: Optional[str] = Query(None, description="备注"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新兑换状态（管理员或用户自己）"""
    try:
        exchange = update_exchange_status(
            db,
            exchange_id,
            status,
            exchange_code=exchange_code,
            notes=notes
        )
        
        if not exchange:
            raise HTTPException(status_code=404, detail="兑换记录不存在")
        
        # 获取商品信息
        product = get_points_product(db, exchange.product_id)
        
        exchange_public = PointsProductExchangePublic.model_validate(exchange)
        exchange_public.product_name = product.name if product else None
        exchange_public.product_image_url = product.image_url if product else None
        # 解析 tags 字段（逗号分隔的字符串）为列表
        if product and product.tags:
            exchange_public.tags = [tag.strip() for tag in product.tags.split(",") if tag.strip()]
        else:
            exchange_public.tags = []
        
        return exchange_public
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新状态失败：{str(e)}")


@router.get("/enums/labels")
def get_product_labels():
    """获取商品标签枚举值"""
    return {
        "labels": [
            {"value": label.value, "label": label.value, "name": label.name}
            for label in PointsProductLabel
        ]
    }


# ==================== 排行榜相关接口 ====================

@router.get("/leaderboard/users", response_model=PointsRedemptionLeaderboardPublic)
def get_user_redemption_leaderboard_endpoint(
    limit: int = Query(100, ge=1, le=100, description="返回数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户积分兑换排行榜"""
    try:
        user_id = current_user.id
        leaderboard, total, user_rank = get_points_redemption_leaderboard(
            db,
            limit=limit,
            user_id=user_id
        )
        
        return PointsRedemptionLeaderboardPublic(
            data=leaderboard,
            count=total,
            user_rank=user_rank
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户排行榜失败：{str(e)}")


@router.get("/leaderboard/products", response_model=ProductExchangeLeaderboardPublic)
def get_product_exchange_leaderboard_endpoint(
    limit: int = Query(100, ge=1, le=100, description="返回数量"),
    db: Session = Depends(get_db)
):
    """获取商品兑换排行榜"""
    try:
        leaderboard, total = get_product_exchange_leaderboard(
            db,
            limit=limit
        )
        
        return ProductExchangeLeaderboardPublic(
            data=leaderboard,
            count=total
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取商品排行榜失败：{str(e)}")

