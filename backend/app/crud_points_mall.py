"""
积分商城CRUD操作
"""
import uuid
import json
from datetime import datetime
from typing import List, Optional, Tuple
from sqlmodel import Session, select, func, desc, and_, or_
from sqlalchemy.orm import selectinload

from app.models import (
    User,
    PointsProductCategory,
    PointsProductCategoryCreate,
    PointsProductCategoryUpdate,
    PointsProduct,
    PointsProductCreate,
    PointsProductUpdate,
    PointsProductExchange,
    PointsProductExchangeCreate,
    PointsProductExchangeUpdate,
    PointsTransaction,
    PointsTransactionCreate,
    PointsProductCategoryType,
    ExchangeStatus,
    PointsSourceType,
    PointsRedemptionLeaderboardEntry,
    ProductExchangeLeaderboardEntry
)


# ==================== 分类相关操作 ====================

def create_points_product_category(
    session: Session,
    category_data: PointsProductCategoryCreate
) -> PointsProductCategory:
    """创建积分商品分类"""
    db_obj = PointsProductCategory.model_validate(
        category_data, update={"id": uuid.uuid4()}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_points_product_category(
    session: Session,
    category_id: uuid.UUID
) -> Optional[PointsProductCategory]:
    """根据ID获取分类"""
    return session.get(PointsProductCategory, category_id)


def get_points_product_categories(
    session: Session,
    category_type: Optional[PointsProductCategoryType] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[PointsProductCategory], int]:
    """获取分类列表"""
    query = select(PointsProductCategory)
    
    filters = []
    if category_type is not None:
        filters.append(PointsProductCategory.category_type == category_type)
    if is_active is not None:
        filters.append(PointsProductCategory.is_active == is_active)
    
    if filters:
        query = query.where(and_(*filters))
    
    # 获取总数
    count_query = select(func.count(PointsProductCategory.id))
    if filters:
        count_query = count_query.where(and_(*filters))
    total = session.exec(count_query).one()
    
    # 获取分页数据
    query = query.order_by(PointsProductCategory.sort_order).offset(skip).limit(limit)
    results = session.exec(query).all()
    
    return results, total


def update_points_product_category(
    session: Session,
    category_id: uuid.UUID,
    category_data: PointsProductCategoryUpdate
) -> Optional[PointsProductCategory]:
    """更新分类"""
    db_obj = session.get(PointsProductCategory, category_id)
    if not db_obj:
        return None
    
    update_data = category_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete_points_product_category(
    session: Session,
    category_id: uuid.UUID
) -> bool:
    """删除分类"""
    db_obj = session.get(PointsProductCategory, category_id)
    if not db_obj:
        return False
    
    session.delete(db_obj)
    session.commit()
    return True


# ==================== 商品相关操作 ====================

def create_points_product(
    session: Session,
    product_data: PointsProductCreate
) -> PointsProduct:
    """创建积分商品"""
    db_obj = PointsProduct.model_validate(
        product_data, update={"id": uuid.uuid4()}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_points_product(
    session: Session,
    product_id: uuid.UUID
) -> Optional[PointsProduct]:
    """根据ID获取商品"""
    return session.get(PointsProduct, product_id)


def get_points_products(
    session: Session,
    category_id: Optional[uuid.UUID] = None,
    category_type: Optional[PointsProductCategoryType] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[PointsProduct], int]:
    """获取商品列表"""
    query = select(PointsProduct)
    
    filters = []
    
    if category_id is not None:
        filters.append(PointsProduct.category_id == category_id)
    
    if category_type is not None:
        # 需要关联分类表查询
        query = query.join(PointsProductCategory)
        filters.append(PointsProductCategory.category_type == category_type)
    
    if is_active is not None:
        filters.append(PointsProduct.is_active == is_active)
    
    if filters:
        query = query.where(and_(*filters))
    
    # 获取总数
    if category_type is not None:
        count_query = select(func.count(PointsProduct.id)).join(PointsProductCategory)
    else:
        count_query = select(func.count(PointsProduct.id))
    
    if filters:
        count_query = count_query.where(and_(*filters))
    total = session.exec(count_query).one()
    
    # 获取分页数据
    query = query.order_by(PointsProduct.sort_order, desc(PointsProduct.created_at)).offset(skip).limit(limit)
    results = session.exec(query).all()
    
    return results, total


def get_hot_exchange_products(
    session: Session,
    limit: int = 4
) -> List[PointsProduct]:
    """获取热门兑换商品（按兑换数量排序）"""
    query = select(PointsProduct).where(
        and_(
            PointsProduct.is_active == True,
            PointsProduct.exchanged_quantity > 0
        )
    ).order_by(desc(PointsProduct.exchanged_quantity)).limit(limit)
    
    results = session.exec(query).all()
    return results


def update_points_product(
    session: Session,
    product_id: uuid.UUID,
    product_data: PointsProductUpdate
) -> Optional[PointsProduct]:
    """更新商品"""
    db_obj = session.get(PointsProduct, product_id)
    if not db_obj:
        return None
    
    update_data = product_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete_points_product(
    session: Session,
    product_id: uuid.UUID
) -> bool:
    """删除商品"""
    db_obj = session.get(PointsProduct, product_id)
    if not db_obj:
        return False
    
    session.delete(db_obj)
    session.commit()
    return True


# ==================== 兑换相关操作 ====================

def exchange_points_product(
    session: Session,
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: int = 1,
    recipient_info: Optional[str] = None
) -> Tuple[Optional[PointsProductExchange], str]:
    """兑换积分商品"""
    try:
        # 获取用户和商品信息
        user = session.get(User, user_id)
        product = session.get(PointsProduct, product_id)
        
        if not user:
            return None, "用户不存在"
        
        if not product:
            return None, "商品不存在"
        
        if not product.is_active:
            return None, "商品已下架"
        
        # 检查商品上架时间
        now = datetime.utcnow()
        if product.start_time and now < product.start_time:
            return None, "商品尚未上架"
        
        if product.end_time and now > product.end_time:
            return None, "商品已下架"
        
        # 检查库存
        if product.total_quantity >= 0 and product.stock_quantity < quantity:
            return None, "库存不足"
        
        # 计算所需积分
        points_needed = product.points_required * quantity
        
        # 检查用户积分余额
        if user.points_balance < points_needed:
            return None, f"积分不足，需要{points_needed}积分，当前仅有{user.points_balance}积分"
        
        # 检查最低积分余额要求
        if product.min_points_balance > 0 and user.points_balance < product.min_points_balance:
            return None, f"兑换该商品需要积分余额不低于{product.min_points_balance}"
        
        # 检查用户兑换次数限制
        if product.max_exchange_per_user > 0:
            user_exchange_count_query = select(func.count(PointsProductExchange.id)).where(
                and_(
                    PointsProductExchange.user_id == user_id,
                    PointsProductExchange.product_id == product_id,
                    PointsProductExchange.status != ExchangeStatus.CANCELLED,
                    PointsProductExchange.status != ExchangeStatus.REFUNDED
                )
            )
            user_exchange_count = session.exec(user_exchange_count_query).one()
            
            if user_exchange_count + quantity > product.max_exchange_per_user:
                return None, f"该商品每用户最多兑换{product.max_exchange_per_user}次"
        
        # 扣除积分
        user.points_balance -= points_needed
        # 更新累计兑换积分
        user.points_redeemed += points_needed
        
        # 更新商品库存和兑换数量
        product.exchanged_quantity += quantity
        if product.total_quantity >= 0:
            product.stock_quantity -= quantity
        
        # 创建积分流水记录
        points_transaction = PointsTransaction(
            id=uuid.uuid4(),
            user_id=user_id,
            points_change=-points_needed,
            balance_after=user.points_balance,
            source_type=PointsSourceType.POINTS_PRODUCT_EXCHANGE,
            source_id=str(product_id),
            description=f"兑换商品：{product.name}",
            created_at=datetime.utcnow()
        )
        session.add(points_transaction)
        
        # 创建兑换记录
        product_snapshot = json.dumps({
            "name": product.name,
            "image_url": product.image_url,
            "points_required": product.points_required,
            "description": product.description
        }, ensure_ascii=False)
        
        exchange = PointsProductExchange(
            id=uuid.uuid4(),
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            points_used=points_needed,
            status=ExchangeStatus.PENDING,
            recipient_info=recipient_info,
            product_snapshot=product_snapshot,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(exchange)
        
        session.commit()
        session.refresh(exchange)
        
        return exchange, "兑换成功"
        
    except Exception as e:
        session.rollback()
        return None, f"兑换失败：{str(e)}"


def get_points_product_exchange(
    session: Session,
    exchange_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None
) -> Optional[PointsProductExchange]:
    """根据ID获取兑换记录"""
    query = select(PointsProductExchange).where(PointsProductExchange.id == exchange_id)
    
    if user_id is not None:
        query = query.where(PointsProductExchange.user_id == user_id)
    
    result = session.exec(query).first()
    return result


def get_user_exchanges(
    session: Session,
    user_id: uuid.UUID,
    status: Optional[ExchangeStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[PointsProductExchange], int]:
    """获取用户的兑换记录"""
    query = select(PointsProductExchange).where(PointsProductExchange.user_id == user_id)
    
    if status is not None:
        query = query.where(PointsProductExchange.status == status)
    
    # 获取总数
    count_query = select(func.count(PointsProductExchange.id)).where(
        PointsProductExchange.user_id == user_id
    )
    if status is not None:
        count_query = count_query.where(PointsProductExchange.status == status)
    total = session.exec(count_query).one()
    
    # 获取分页数据
    query = query.order_by(desc(PointsProductExchange.created_at)).offset(skip).limit(limit)
    results = session.exec(query).all()
    
    return results, total


def update_exchange_status(
    session: Session,
    exchange_id: uuid.UUID,
    status: ExchangeStatus,
    exchange_code: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[PointsProductExchange]:
    """更新兑换状态"""
    exchange = session.get(PointsProductExchange, exchange_id)
    if not exchange:
        return None
    
    old_status = exchange.status
    exchange.status = status
    exchange.updated_at = datetime.utcnow()
    
    if exchange_code:
        exchange.exchange_code = exchange_code
    
    if notes:
        exchange.notes = notes
    
    # 根据状态更新时间字段
    if status == ExchangeStatus.ISSUED and old_status != ExchangeStatus.ISSUED:
        exchange.issued_at = datetime.utcnow()
    elif status == ExchangeStatus.USED and old_status != ExchangeStatus.USED:
        exchange.used_at = datetime.utcnow()
    elif status == ExchangeStatus.REFUNDED and old_status != ExchangeStatus.REFUNDED:
        exchange.refunded_at = datetime.utcnow()
        
        # 退款：返还积分
        user = session.get(User, exchange.user_id)
        if user:
            user.points_balance += exchange.points_used
            # 减少累计兑换积分
            user.points_redeemed = max(0, user.points_redeemed - exchange.points_used)
            
            # 创建积分流水记录
            points_transaction = PointsTransaction(
                id=uuid.uuid4(),
                user_id=exchange.user_id,
                points_change=exchange.points_used,
                balance_after=user.points_balance,
                source_type=PointsSourceType.POINTS_PRODUCT_REFUND,
                source_id=str(exchange.product_id),
                description=f"兑换退款",
                created_at=datetime.utcnow()
            )
            session.add(points_transaction)
            
            # 恢复商品库存
            product = session.get(PointsProduct, exchange.product_id)
            if product:
                product.exchanged_quantity = max(0, product.exchanged_quantity - exchange.quantity)
                if product.total_quantity >= 0:
                    product.stock_quantity += exchange.quantity
    
    session.commit()
    session.refresh(exchange)
    return exchange


# ==================== 排行榜相关操作 ====================

def get_points_redemption_leaderboard(
    session: Session,
    limit: int = 100,
    user_id: Optional[uuid.UUID] = None
) -> Tuple[List[PointsRedemptionLeaderboardEntry], int, Optional[int]]:
    """获取积分兑换排行榜"""
    # 查询累计兑换积分大于0的用户，按兑换积分降序排列
    query = select(User).where(
        and_(
            User.is_active == True,
            User.points_redeemed > 0
        )
    ).order_by(desc(User.points_redeemed))
    
    # 获取总数
    count_query = select(func.count(User.id)).where(
        and_(
            User.is_active == True,
            User.points_redeemed > 0
        )
    )
    total = session.exec(count_query).one() or 0
    
    # 获取分页数据
    query = query.limit(limit)
    results = session.exec(query).all()
    
    # 构建排行榜条目
    leaderboard = []
    user_rank = None
    
    for rank, user in enumerate(results, 1):
        entry = PointsRedemptionLeaderboardEntry(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            points_redeemed=user.points_redeemed,
            rank=rank,
            avatar_url=user.avatar_url
        )
        leaderboard.append(entry)
        
        if user_id and user.id == user_id:
            user_rank = rank
            
    # 如果用户不在前limit名中，单独查询其排名
    if user_id and user_rank is None:
        user = session.get(User, user_id)
        if user and user.points_redeemed > 0:
            # 计算排名：积分比他多的人数 + 1
            rank_query = select(func.count(User.id)).where(
                and_(
                    User.is_active == True,
                    User.points_redeemed > user.points_redeemed
                )
            )
            higher_rank_count = session.exec(rank_query).one() or 0
            user_rank = higher_rank_count + 1
            
    return leaderboard, total, user_rank


def get_product_exchange_leaderboard(
    session: Session,
    limit: int = 100
) -> Tuple[List[ProductExchangeLeaderboardEntry], int]:
    """获取商品兑换排行榜"""
    # 查询兑换数量大于0的商品，按兑换数量降序排列
    query = select(PointsProduct).where(
        and_(
            PointsProduct.is_active == True,
            PointsProduct.exchanged_quantity > 0
        )
    ).order_by(desc(PointsProduct.exchanged_quantity))
    
    # 获取总数
    count_query = select(func.count(PointsProduct.id)).where(
        and_(
            PointsProduct.is_active == True,
            PointsProduct.exchanged_quantity > 0
        )
    )
    total = session.exec(count_query).one() or 0
    
    # 获取分页数据
    query = query.limit(limit)
    results = session.exec(query).all()
    
    # 构建排行榜条目
    leaderboard = []
    
    for rank, product in enumerate(results, 1):
        # 获取分类名称
        category = session.get(PointsProductCategory, product.category_id)
        
        # 解析标签
        tags = []
        if product.tags:
            tags = [tag.strip() for tag in product.tags.split(",") if tag.strip()]
        
        entry = ProductExchangeLeaderboardEntry(
            product_id=product.id,
            product_name=product.name,
            product_image_url=product.image_url,
            exchanged_quantity=product.exchanged_quantity,
            points_required=product.points_required,
            rank=rank,
            category_name=category.name if category else None,
            tags=tags
        )
        leaderboard.append(entry)
    
    return leaderboard, total
