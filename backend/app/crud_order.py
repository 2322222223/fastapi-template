import json
import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlmodel import Session, select, and_, or_, func

from app.models import (
    Order,
    OrderCreate,
    OrderUpdate,
    OrderItem,
    OrderItemCreate,
    OrderItemWithProduct,
    OrderWithItems,
    OrderStatus,
    OrderStats,
    CartItem,
    Product,
    Store,
    UserCoupon,
    UserCouponPublic,
)
from app.utils import generate_pickup_code


# ==================== 订单 CRUD ====================

def generate_order_number() -> str:
    """生成订单号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = str(uuid.uuid4())[:8].upper()
    return f"ORD{timestamp}{random_suffix}"


def create_product_snapshot(product: Product) -> str:
    """创建商品快照"""
    snapshot = {
        "id": str(product.id),
        "title": product.title,
        "subtitle": product.subtitle,
        "price": product.price,
        "original_price": product.original_price,
        "discount": product.discount,
        "image_url": product.image_url,
        "tag": product.tag,
        "sales_count": product.sales_count,
        "category": product.category,
        "member_price": product.member_price,
        "coupon_saved": product.coupon_saved,
        "total_saved": product.total_saved,
        "store_id": str(product.store_id),
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat()
    }
    return json.dumps(snapshot, ensure_ascii=False)


def create_order_from_cart(
    session: Session,
    user_id: UUID,
    cart_item_ids: List[UUID],
    shipping_address: Optional[str] = "",
    billing_address: Optional[str] = None,
    customer_notes: Optional[str] = None,
    coupon_id: Optional[str] = None
) -> Order:
    """从购物车创建订单"""
    
    # 1. 获取购物车项
    cart_items = session.exec(
        select(CartItem).where(
            and_(
                CartItem.id.in_(cart_item_ids),
                CartItem.user_id == user_id,
                CartItem.is_selected == True
            )
        )
    ).all()
    
    if not cart_items:
        raise ValueError("购物车中没有选中的商品")
    
    # 2. 计算订单金额
    subtotal_amount = sum(item.total_price for item in cart_items)
    shipping_fee = 0.0  # 可以根据业务规则计算
    tax_amount = 0.0    # 可以根据业务规则计算
    discount_amount = 0.0
    
    # 3. 处理优惠券
    if coupon_id and coupon_id.strip():  # 检查不为空字符串
        try:
            coupon_uuid = UUID(coupon_id)
            coupon = session.exec(
                select(UserCoupon).where(
                    and_(
                        UserCoupon.id == coupon_uuid,
                        UserCoupon.user_id == user_id,
                        UserCoupon.status == 0  # 未使用
                    )
                )
            ).first()
        except ValueError:
            # 如果 coupon_id 不是有效的 UUID，忽略优惠券
            coupon = None
        
        if coupon:
            # 检查优惠券使用条件
            if subtotal_amount >= coupon.min_spend:
                if coupon.coupon_type == 1:  # 满减券
                    discount_amount = min(coupon.value, subtotal_amount)
                elif coupon.coupon_type == 2:  # 折扣券
                    discount_amount = subtotal_amount * (1 - coupon.value / 100)
                elif coupon.coupon_type == 3:  # 运费抵扣券
                    discount_amount = min(coupon.value, shipping_fee)
                    shipping_fee = max(0, shipping_fee - discount_amount)
    
    total_amount = subtotal_amount + shipping_fee + tax_amount - discount_amount
    
    # 4. 创建订单
    order_number = generate_order_number()
    order = Order(
        order_number=order_number,
        user_id=user_id,
        status=OrderStatus.PENDING_PAYMENT,
        subtotal_amount=subtotal_amount,
        shipping_fee=shipping_fee,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        shipping_address=shipping_address,
        billing_address=billing_address,
        payment_method=None,  # 支付方式在支付时确定
        customer_notes=customer_notes
    )
    
    session.add(order)
    session.flush()  # 获取订单ID
    
    # 5. 创建订单项
    for cart_item in cart_items:
        # 获取商品信息
        product = session.exec(
            select(Product).where(Product.id == cart_item.product_id)
        ).first()
        
        if not product:
            raise ValueError(f"商品不存在: {cart_item.product_id}")
        
        # 创建商品快照
        product_snapshot = create_product_snapshot(product)
        
        # 创建订单项
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            product_snapshot=product_snapshot,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.total_price
        )
        
        session.add(order_item)
    
    # 6. 更新优惠券状态
    if coupon_id and coupon_id.strip() and discount_amount > 0 and coupon:
        coupon.status = 1  # 已使用
        coupon.order_id = order.id
        session.add(coupon)
    
    # 7. 删除购物车项
    for cart_item in cart_items:
        session.delete(cart_item)
    
    session.commit()
    session.refresh(order)
    
    return order


def get_order(session: Session, order_id: UUID, user_id: Optional[UUID] = None) -> Optional[Order]:
    """获取订单"""
    query = select(Order).where(
        and_(
            Order.id == order_id,
            Order.is_deleted == False  # 过滤软删除的订单
        )
    )
    if user_id:
        query = query.where(Order.user_id == user_id)
    return session.exec(query).first()


def get_orders(
    session: Session,
    user_id: Optional[UUID] = None,
    status: Optional[OrderStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Order]:
    """获取订单列表"""
    query = select(Order).where(Order.is_deleted == False)  # 过滤软删除的订单
    
    if user_id:
        query = query.where(Order.user_id == user_id)
    
    if status:
        query = query.where(Order.status == status)
    
    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
    
    return session.exec(query).all()


def get_orders_with_details(
    session: Session,
    user_id: Optional[UUID] = None,
    status: Optional[OrderStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[OrderWithItems]:
    """获取包含详情的订单列表"""
    # 先获取基本订单列表
    orders = get_orders(session, user_id, status, skip, limit)
    
    # 为每个订单获取详细信息
    orders_with_details = []
    for order in orders:
        order_with_items = get_order_with_items(session, order.id, user_id)
        if order_with_items:
            orders_with_details.append(order_with_items)
    
    return orders_with_details


def get_orders_count(
    session: Session,
    user_id: Optional[UUID] = None,
    status: Optional[OrderStatus] = None
) -> int:
    """获取订单数量"""
    query = select(func.count(Order.id)).where(Order.is_deleted == False)  # 过滤软删除的订单
    
    if user_id:
        query = query.where(Order.user_id == user_id)
    
    if status:
        query = query.where(Order.status == status)
    
    return session.exec(query).one()


def update_order_status(
    session: Session,
    order_id: UUID,
    status: OrderStatus,
    internal_notes: Optional[str] = None,
    payment_gateway_txn_id: Optional[str] = None,
    user_id: Optional[UUID] = None
) -> Optional[Order]:
    """更新订单状态"""
    query = select(Order).where(
        and_(
            Order.id == order_id,
            Order.is_deleted == False  # 过滤软删除的订单
        )
    )
    if user_id:
        query = query.where(Order.user_id == user_id)
    
    order = session.exec(query).first()
    if not order:
        return None
    
    # 更新状态
    order.status = status
    order.updated_at = datetime.utcnow()
    
    # 根据状态设置相应的时间戳和生成取餐码
    if status == OrderStatus.PROCESSING and not order.paid_at:
        order.paid_at = datetime.utcnow()
        # 生成取餐码
        if not order.pickup_code:
            order.pickup_code = generate_pickup_code()
            order.pickup_code_generated_at = datetime.utcnow()
    elif status == OrderStatus.SHIPPED and not order.shipped_at:
        order.shipped_at = datetime.utcnow()
    elif status == OrderStatus.COMPLETED and not order.completed_at:
        order.completed_at = datetime.utcnow()
    
    if internal_notes:
        order.internal_notes = internal_notes
    
    if payment_gateway_txn_id:
        order.payment_gateway_txn_id = payment_gateway_txn_id
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return order


def cancel_order(session: Session, order_id: UUID, user_id: UUID) -> Optional[Order]:
    """取消订单"""
    order = session.exec(
        select(Order).where(
            and_(
                Order.id == order_id,
                Order.user_id == user_id,
                Order.status == OrderStatus.PENDING_PAYMENT,
                Order.is_deleted == False  # 过滤软删除的订单
            )
        )
    ).first()
    
    if not order:
        return None
    
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return order


def get_order_with_items(session: Session, order_id: UUID, user_id: Optional[UUID] = None) -> Optional[OrderWithItems]:
    """获取包含订单项的完整订单信息"""
    query = select(Order).where(
        and_(
            Order.id == order_id,
            Order.is_deleted == False  # 过滤软删除的订单
        )
    )
    if user_id:
        query = query.where(Order.user_id == user_id)
    
    order = session.exec(query).first()
    if not order:
        return None
    
    # 获取订单项
    order_items = session.exec(
        select(OrderItem).where(OrderItem.order_id == order_id)
    ).all()
    
    # 构建返回数据
    order_with_items = OrderWithItems(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        subtotal_amount=order.subtotal_amount,
        shipping_fee=order.shipping_fee,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        payment_method=order.payment_method,
        payment_gateway_txn_id=order.payment_gateway_txn_id,
        customer_notes=order.customer_notes,
        internal_notes=order.internal_notes,
        paid_at=order.paid_at,
        shipped_at=order.shipped_at,
        completed_at=order.completed_at,
        pickup_code=order.pickup_code,
        pickup_code_generated_at=order.pickup_code_generated_at,
        pickup_code_verified_at=order.pickup_code_verified_at,
        user_id=order.user_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        order_items=[]
    )
    
    # 添加订单项
    for item in order_items:
        # 解析商品快照
        try:
            product_snapshot = json.loads(item.product_snapshot)
            product_info = {
                "id": product_snapshot["id"],
                "title": product_snapshot["title"],
                "subtitle": product_snapshot["subtitle"],
                "price": product_snapshot["price"],
                "original_price": product_snapshot["original_price"],
                "discount": product_snapshot["discount"],
                "image_url": product_snapshot["image_url"],
                "tag": product_snapshot["tag"],
                "sales_count": product_snapshot["sales_count"],
                "category": product_snapshot["category"],
                "member_price": product_snapshot.get("member_price"),
                "coupon_saved": product_snapshot.get("coupon_saved"),
                "total_saved": product_snapshot.get("total_saved"),
                "store_id": product_snapshot["store_id"],
                "created_at": product_snapshot["created_at"],
                "updated_at": product_snapshot["updated_at"]
            }
        except (json.JSONDecodeError, KeyError):
            product_info = None
        
        # 获取店铺信息
        store_info = None
        try:
            if product_info and "store_id" in product_info:
                store = session.exec(
                    select(Store).where(Store.id == UUID(product_info["store_id"]))
                ).first()
                if store:
                    store_info = {
                        "id": str(store.id),
                        "name": store.name,
                        "category": store.category,
                        "rating": store.rating,
                        "review_count": store.review_count,
                        "price_range": store.price_range,
                        "location": store.location,
                        "floor": store.floor,
                        "image_url": store.image_url,
                        "tags": store.tags,
                        "is_live": store.is_live,
                        "has_delivery": store.has_delivery,
                        "distance": store.distance,
                        "title": store.title,
                        "sub_title": store.sub_title,
                        "sub_icon": store.sub_icon,
                        "business_district_id": str(store.business_district_id)
                    }
        except (ValueError, KeyError):
            store_info = None
        
        order_item_with_product = OrderItemWithProduct(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_id,
            product_snapshot=item.product_snapshot,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            created_at=item.created_at,
            updated_at=item.updated_at,
            product=product_info,
            store=store_info
        )
        
        order_with_items.order_items.append(order_item_with_product)
    
    return order_with_items


def get_order_stats(session: Session, user_id: Optional[UUID] = None) -> OrderStats:
    """获取订单统计信息"""
    base_query = select(Order).where(Order.is_deleted == False)  # 过滤软删除的订单
    if user_id:
        base_query = base_query.where(Order.user_id == user_id)
    
    # 总订单数
    if user_id:
        total_orders = session.exec(
            select(func.count(Order.id)).where(
                and_(
                    Order.user_id == user_id,
                    Order.is_deleted == False
                )
            )
        ).one()
    else:
        total_orders = session.exec(
            select(func.count(Order.id)).where(Order.is_deleted == False)
        ).one()
    
    # 各状态订单数
    def get_status_count(status: OrderStatus) -> int:
        query = select(func.count(Order.id)).where(
            and_(
                Order.status == status,
                Order.is_deleted == False
            )
        )
        if user_id:
            query = query.where(Order.user_id == user_id)
        return session.exec(query).one()
    
    pending_payment = get_status_count(OrderStatus.PENDING_PAYMENT)
    processing = get_status_count(OrderStatus.PROCESSING)
    shipped = get_status_count(OrderStatus.SHIPPED)
    completed = get_status_count(OrderStatus.COMPLETED)
    cancelled = get_status_count(OrderStatus.CANCELLED)
    
    # 总金额
    total_amount_query = select(func.sum(Order.total_amount)).where(Order.is_deleted == False)
    if user_id:
        total_amount_query = total_amount_query.where(Order.user_id == user_id)
    
    total_amount = session.exec(total_amount_query).one() or 0.0
    
    return OrderStats(
        total_orders=total_orders,
        pending_payment=pending_payment,
        processing=processing,
        shipped=shipped,
        completed=completed,
        cancelled=cancelled,
        total_amount=total_amount
    )


def delete_order(session: Session, order_id: UUID, user_id: UUID) -> bool:
    """软删除订单（不能删除已完成、已发货、已送达、已退款的订单）"""
    # 不能删除的状态
    protected_statuses = {
        OrderStatus.COMPLETED,    # 已完成
        OrderStatus.SHIPPED,      # 已发货
        OrderStatus.DELIVERED,    # 已送达
        OrderStatus.REFUNDED      # 已退款
    }
    
    order = session.exec(
        select(Order).where(
            and_(
                Order.id == order_id,
                Order.user_id == user_id,
                Order.is_deleted == False,  # 确保未删除
                ~Order.status.in_(protected_statuses)  # 不在保护状态中
            )
        )
    ).first()
    
    if not order:
        return False
    
    # 软删除
    order.is_deleted = True
    order.deleted_at = datetime.utcnow()
    session.commit()
    return True


def get_order_by_pickup_code(session: Session, pickup_code: str) -> Optional[Order]:
    """通过取餐码查找订单"""
    return session.exec(
        select(Order).where(
            and_(
                Order.pickup_code == pickup_code,
                Order.is_deleted == False
            )
        )
    ).first()


def verify_pickup_code(session: Session, pickup_code: str) -> Optional[Order]:
    """核销取餐码"""
    order = get_order_by_pickup_code(session, pickup_code)
    
    if not order:
        return None
    
    # 检查订单状态是否为PROCESSING
    if order.status != OrderStatus.PROCESSING:
        return None
    
    # 检查取餐码是否已经被核销
    if order.pickup_code_verified_at:
        return None
    
    # 更新订单状态为已完成
    order.status = OrderStatus.COMPLETED
    order.pickup_code_verified_at = datetime.utcnow()
    order.completed_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()
    
    session.add(order)
    session.commit()
    session.refresh(order)
    
    return order
