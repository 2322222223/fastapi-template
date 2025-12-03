from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlmodel import Session, select, and_, or_

from app.models import (
    CartItem,
    CartItemCreate,
    CartItemUpdate,
    CartItemWithDetails,
    CartSummary,
    CartStoreGroup,
    Product,
    Store,
)


# ==================== 购物车 CRUD ====================

def create_cart_item(session: Session, cart_item: CartItemCreate, user_id: UUID) -> CartItem:
    """添加商品到购物车"""
    # 检查是否已存在相同的商品（相同商品ID、规格、店铺）
    existing_statement = select(CartItem).where(
        and_(
            CartItem.user_id == user_id,
            CartItem.product_id == cart_item.product_id,
            CartItem.store_id == cart_item.store_id,
            CartItem.product_spec == cart_item.product_spec
        )
    )
    existing_item = session.exec(existing_statement).first()
    
    if existing_item:
        # 如果已存在，增加数量
        existing_item.quantity += cart_item.quantity
        existing_item.total_price = existing_item.quantity * existing_item.unit_price
        existing_item.updated_at = datetime.utcnow()
        session.add(existing_item)
        session.commit()
        session.refresh(existing_item)
        return existing_item
    else:
        # 创建新的购物车项
        db_cart_item = CartItem(
            user_id=user_id,
            product_id=cart_item.product_id,
            store_id=cart_item.store_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.total_price,
            is_selected=cart_item.is_selected,
            product_spec=cart_item.product_spec,
            notes=cart_item.notes
        )
        session.add(db_cart_item)
        session.commit()
        session.refresh(db_cart_item)
        return db_cart_item


def create_cart_item_simple(session: Session, cart_item_simple, user_id: UUID) -> CartItem:
    """简化的添加商品到购物车 - 自动从Product获取信息"""
    # 先获取商品信息
    product = session.exec(select(Product).where(Product.id == cart_item_simple.product_id)).first()
    if not product:
        raise ValueError("商品不存在")
    
    # 检查是否已存在相同的商品（相同商品ID、规格、店铺）
    existing_statement = select(CartItem).where(
        and_(
            CartItem.user_id == user_id,
            CartItem.product_id == cart_item_simple.product_id,
            CartItem.store_id == product.store_id,
            CartItem.product_spec == cart_item_simple.product_spec
        )
    )
    existing_item = session.exec(existing_statement).first()
    
    if existing_item:
        # 如果已存在，增加数量
        existing_item.quantity += cart_item_simple.quantity
        existing_item.total_price = existing_item.quantity * existing_item.unit_price
        existing_item.updated_at = datetime.utcnow()
        session.add(existing_item)
        session.commit()
        session.refresh(existing_item)
        return existing_item
    else:
        # 创建新的购物车项，自动从Product获取信息
        unit_price = product.price  # 使用商品当前价格
        total_price = unit_price * cart_item_simple.quantity
        
        db_cart_item = CartItem(
            user_id=user_id,
            product_id=cart_item_simple.product_id,
            store_id=product.store_id,  # 自动从Product获取
            quantity=cart_item_simple.quantity,
            unit_price=unit_price,  # 自动从Product获取
            total_price=total_price,
            is_selected=True,
            product_spec=cart_item_simple.product_spec,
            notes=cart_item_simple.notes
        )
        session.add(db_cart_item)
        session.commit()
        session.refresh(db_cart_item)
        return db_cart_item


def get_cart_item(session: Session, cart_item_id: UUID) -> Optional[CartItem]:
    """获取购物车项"""
    statement = select(CartItem).where(CartItem.id == cart_item_id)
    return session.exec(statement).first()


def get_cart_items_by_user(
    session: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    store_id: Optional[UUID] = None,
    is_selected: Optional[bool] = None
) -> Tuple[List[CartItem], bool]:
    """获取用户的购物车项列表"""
    statement = select(CartItem).where(CartItem.user_id == user_id)
    
    if store_id:
        statement = statement.where(CartItem.store_id == store_id)
    
    if is_selected is not None:
        statement = statement.where(CartItem.is_selected == is_selected)
    
    statement = statement.offset(skip).limit(limit + 1).order_by(CartItem.created_at.desc())
    items = list(session.exec(statement).all())
    
    # 判断是否还有更多数据
    is_more = len(items) > limit
    if is_more:
        items = items[:limit]
    
    return items, is_more


def get_cart_items_with_details(
    session: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    store_id: Optional[UUID] = None,
    is_selected: Optional[bool] = None
) -> Tuple[List[CartItemWithDetails], bool]:
    """获取包含商品和店铺详情的购物车项列表"""
    statement = select(CartItem).where(CartItem.user_id == user_id)
    
    if store_id:
        statement = statement.where(CartItem.store_id == store_id)
    
    if is_selected is not None:
        statement = statement.where(CartItem.is_selected == is_selected)
    
    statement = statement.offset(skip).limit(limit + 1).order_by(CartItem.created_at.desc())
    items = list(session.exec(statement).all())
    
    # 判断是否还有更多数据
    is_more = len(items) > limit
    if is_more:
        items = items[:limit]
    
    # 构建包含详情的购物车项
    items_with_details = []
    for item in items:
        # 获取商品详情
        product_statement = select(Product).where(Product.id == item.product_id)
        product = session.exec(product_statement).first()
        
        # 价格同步：如果商品价格发生变化，更新购物车项价格
        if product and product.price != item.unit_price:
            item.unit_price = product.price
            item.total_price = item.quantity * item.unit_price
            item.updated_at = datetime.utcnow()
            session.add(item)
            session.commit()
            session.refresh(item)
        
        # 获取店铺详情
        store_statement = select(Store).where(Store.id == item.store_id)
        store = session.exec(store_statement).first()
        
        # 构建详情对象
        item_detail = CartItemWithDetails(
            id=item.id,
            user_id=item.user_id,
            product_id=item.product_id,
            store_id=item.store_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            is_selected=item.is_selected,
            product_spec=item.product_spec,
            notes=item.notes,
            created_at=item.created_at,
            updated_at=item.updated_at,
            product=product,
            store=store
        )
        items_with_details.append(item_detail)
    
    return items_with_details, is_more


def update_cart_item(
    session: Session,
    cart_item_id: UUID,
    cart_item_update: CartItemUpdate
) -> Optional[CartItem]:
    """更新购物车项"""
    db_cart_item = get_cart_item(session, cart_item_id)
    if not db_cart_item:
        return None
    
    update_data = cart_item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_cart_item, field, value)
    
    # 如果更新了数量，重新计算总价
    if 'quantity' in update_data:
        db_cart_item.total_price = db_cart_item.quantity * db_cart_item.unit_price
    
    db_cart_item.updated_at = datetime.utcnow()
    session.add(db_cart_item)
    session.commit()
    session.refresh(db_cart_item)
    return db_cart_item


def delete_cart_item(session: Session, cart_item_id: UUID) -> bool:
    """删除购物车项"""
    db_cart_item = get_cart_item(session, cart_item_id)
    if not db_cart_item:
        return False
    
    session.delete(db_cart_item)
    session.commit()
    return True


def clear_cart_by_user(session: Session, user_id: UUID, store_id: Optional[UUID] = None) -> int:
    """清空用户购物车"""
    statement = select(CartItem).where(CartItem.user_id == user_id)
    
    if store_id:
        statement = statement.where(CartItem.store_id == store_id)
    
    items = session.exec(statement).all()
    count = len(items)
    
    for item in items:
        session.delete(item)
    
    session.commit()
    return count


def get_cart_summary(session: Session, user_id: UUID) -> CartSummary:
    """获取购物车汇总信息"""
    # 获取所有购物车项
    statement = select(CartItem).where(CartItem.user_id == user_id)
    items = list(session.exec(statement).all())
    
    # 价格同步：确保购物车项价格与商品价格一致
    price_updated = False
    for item in items:
        product = session.exec(select(Product).where(Product.id == item.product_id)).first()
        if product and product.price != item.unit_price:
            item.unit_price = product.price
            item.total_price = item.quantity * item.unit_price
            item.updated_at = datetime.utcnow()
            session.add(item)
            price_updated = True
    
    if price_updated:
        session.commit()
        # 重新获取更新后的数据
        items = list(session.exec(statement).all())
    
    total_items = len(items)
    total_quantity = sum(item.quantity for item in items)
    total_amount = sum(item.total_price for item in items)
    
    # 选中项统计
    selected_items = [item for item in items if item.is_selected]
    selected_quantity = sum(item.quantity for item in selected_items)
    selected_amount = sum(item.total_price for item in selected_items)
    
    # 店铺数量统计
    store_ids = set(item.store_id for item in items)
    store_count = len(store_ids)
    
    return CartSummary(
        total_items=total_items,
        total_quantity=total_quantity,
        total_amount=total_amount,
        selected_items=len(selected_items),
        selected_quantity=selected_quantity,
        selected_amount=selected_amount,
        store_count=store_count
    )


def get_cart_store_groups(session: Session, user_id: UUID) -> List[CartStoreGroup]:
    """获取按店铺分组的购物车"""
    # 获取所有购物车项
    statement = select(CartItem).where(CartItem.user_id == user_id)
    items = list(session.exec(statement).all())
    
    # 按店铺分组
    store_groups = {}
    for item in items:
        store_id = item.store_id
        if store_id not in store_groups:
            store_groups[store_id] = []
        store_groups[store_id].append(item)
    
    # 构建店铺组信息
    result = []
    for store_id, store_items in store_groups.items():
        # 获取店铺信息
        store_statement = select(Store).where(Store.id == store_id)
        store = session.exec(store_statement).first()
        
        if not store:
            continue
        
        # 构建包含详情的购物车项
        items_with_details = []
        for item in store_items:
            # 获取商品详情
            product_statement = select(Product).where(Product.id == item.product_id)
            product = session.exec(product_statement).first()
            
            item_detail = CartItemWithDetails(
                id=item.id,
                user_id=item.user_id,
                product_id=item.product_id,
                store_id=item.store_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price,
                is_selected=item.is_selected,
                product_spec=item.product_spec,
                notes=item.notes,
                created_at=item.created_at,
                updated_at=item.updated_at,
                product=product,
                store=store
            )
            items_with_details.append(item_detail)
        
        # 计算店铺总金额
        store_total_amount = sum(item.total_price for item in store_items)
        store_selected_amount = sum(item.total_price for item in store_items if item.is_selected)
        
        store_group = CartStoreGroup(
            store_id=store_id,
            store_name=store.name,
            store_image_url=store.image_url,
            items=items_with_details,
            store_total_amount=store_total_amount,
            store_selected_amount=store_selected_amount
        )
        result.append(store_group)
    
    return result


def batch_update_cart_items(
    session: Session,
    user_id: UUID,
    updates: List[dict]
) -> List[CartItem]:
    """批量更新购物车项"""
    updated_items = []
    
    for update_data in updates:
        cart_item_id = update_data.get('id')
        if not cart_item_id:
            continue
        
        # 验证购物车项属于当前用户
        cart_item = get_cart_item(session, cart_item_id)
        if not cart_item or cart_item.user_id != user_id:
            continue
        
        # 更新字段
        for field, value in update_data.items():
            if field != 'id' and hasattr(cart_item, field):
                setattr(cart_item, field, value)
        
        # 如果更新了数量，重新计算总价
        if 'quantity' in update_data:
            cart_item.total_price = cart_item.quantity * cart_item.unit_price
        
        cart_item.updated_at = datetime.utcnow()
        session.add(cart_item)
        updated_items.append(cart_item)
    
    session.commit()
    for item in updated_items:
        session.refresh(item)
    
    return updated_items


def batch_delete_cart_items(session: Session, user_id: UUID, cart_item_ids: List[UUID]) -> int:
    """批量删除购物车项"""
    deleted_count = 0
    
    for cart_item_id in cart_item_ids:
        cart_item = get_cart_item(session, cart_item_id)
        if cart_item and cart_item.user_id == user_id:
            session.delete(cart_item)
            deleted_count += 1
    
    session.commit()
    return deleted_count
