from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.crud_order import (
    create_order_from_cart,
    get_order,
    get_orders,
    get_orders_with_details,
    get_orders_count,
    get_order_with_items,
    get_order_stats,
    update_order_status,
    cancel_order,
    delete_order,
    get_order_by_pickup_code,
    verify_pickup_code,
)
from app.models import (
    Order,
    OrderPublic,
    OrdersPublic,
    OrdersWithDetailsPublic,
    OrderWithItems,
    OrderStats,
    CreateOrderRequest,
    PaymentRequest,
    UpdateOrderStatusRequest,
    VerifyPickupCodeRequest,
    OrderStatus,
)

router = APIRouter()


# ==================== 订单基础接口 ====================

@router.post("/", response_model=OrderPublic)
def create_order(
    order_request: CreateOrderRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Order:
    """创建订单"""
    try:
        order = create_order_from_cart(
            session=session,
            user_id=current_user.id,
            cart_item_ids=order_request.cart_item_ids,
            shipping_address=order_request.shipping_address or "",
            billing_address=order_request.billing_address,
            customer_notes=order_request.customer_notes,
            coupon_id=order_request.coupon_id
        )
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建订单失败: {str(e)}")


@router.get("/", response_model=OrdersWithDetailsPublic)
def get_my_orders(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="订单状态过滤"),
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
) -> OrdersWithDetailsPublic:
    """获取我的订单列表（包含详情）"""
    skip = page * limit
    
    # 处理状态参数
    order_status = None
    if status and status.strip():  # 如果status不为空且不是空白字符串
        try:
            order_status = OrderStatus(status.strip())
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的订单状态: {status}. 有效状态: {[s.value for s in OrderStatus]}"
            )
    
    # 获取包含详情的订单列表
    orders = get_orders_with_details(
        session=session,
        user_id=current_user.id,
        status=order_status,
        skip=skip,
        limit=limit
    )
    
    # 获取总数
    total_count = get_orders_count(
        session=session,
        user_id=current_user.id,
        status=order_status
    )
    
    is_more = page * limit < total_count
    
    return OrdersWithDetailsPublic(data=orders, count=total_count, is_more=is_more)


@router.get("/stats", response_model=OrderStats)
def get_my_order_stats(
    session: SessionDep,
    current_user: CurrentUser,
) -> OrderStats:
    """获取我的订单统计信息"""
    return get_order_stats(session=session, user_id=current_user.id)


@router.get("/{order_id}", response_model=OrderWithItems)
def get_order_detail(
    order_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> OrderWithItems:
    """获取订单详情"""
    order = get_order_with_items(
        session=session,
        order_id=order_id,
        user_id=current_user.id
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    return order


@router.put("/{order_id}/cancel", response_model=OrderPublic)
def cancel_my_order(
    order_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Order:
    """取消订单"""
    order = cancel_order(
        session=session,
        order_id=order_id,
        user_id=current_user.id
    )
    
    if not order:
        raise HTTPException(
            status_code=404, 
            detail="订单不存在或无法取消（只能取消待支付状态的订单）"
        )
    
    return order


@router.delete("/{order_id}")
def delete_my_order(
    order_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """删除订单（仅限已取消的订单）"""
    success = delete_order(
        session=session,
        order_id=order_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="订单不存在或无法删除（不能删除已完成、已发货、已送达、已退款的订单）"
        )
    
    return {"message": "订单已删除"}


# ==================== 管理员接口 ====================

@router.get("/admin/all", response_model=OrdersPublic, dependencies=[Depends(get_current_active_superuser)])
def get_all_orders(
    *,
    session: SessionDep,
    status: Optional[str] = Query(None, description="订单状态过滤"),
    user_id: Optional[UUID] = Query(None, description="用户ID过滤"),
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
) -> OrdersPublic:
    """获取所有订单列表（管理员）"""
    skip = page * limit
    
    # 处理状态参数
    order_status = None
    if status and status.strip():  # 如果status不为空且不是空白字符串
        try:
            order_status = OrderStatus(status.strip())
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的订单状态: {status}. 有效状态: {[s.value for s in OrderStatus]}"
            )
    
    # 获取订单列表
    orders = get_orders(
        session=session,
        user_id=user_id,
        status=order_status,
        skip=skip,
        limit=limit
    )
    
    # 获取总数
    total_count = get_orders_count(
        session=session,
        user_id=user_id,
        status=order_status
    )
    
    is_more = page * limit < total_count
    
    return OrdersPublic(data=orders, count=total_count, is_more=is_more)


@router.get("/admin/stats", response_model=OrderStats, dependencies=[Depends(get_current_active_superuser)])
def get_all_order_stats(
    session: SessionDep,
) -> OrderStats:
    """获取所有订单统计信息（管理员）"""
    return get_order_stats(session=session, user_id=None)


@router.get("/admin/{order_id}", response_model=OrderWithItems, dependencies=[Depends(get_current_active_superuser)])
def get_order_detail_admin(
    order_id: UUID,
    session: SessionDep,
) -> OrderWithItems:
    """获取订单详情（管理员）"""
    order = get_order_with_items(
        session=session,
        order_id=order_id,
        user_id=None
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    return order


@router.put("/admin/{order_id}/status", response_model=OrderPublic, dependencies=[Depends(get_current_active_superuser)])
def update_order_status_admin(
    order_id: UUID,
    status_request: UpdateOrderStatusRequest,
    session: SessionDep,
) -> Order:
    """更新订单状态（管理员）"""
    order = update_order_status(
        session=session,
        order_id=order_id,
        status=status_request.status,
        internal_notes=status_request.internal_notes,
        payment_gateway_txn_id=status_request.payment_gateway_txn_id,
        user_id=None
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    return order


@router.delete("/admin/{order_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_order_admin(
    order_id: UUID,
    session: SessionDep,
) -> dict:
    """软删除订单（管理员）"""
    # 管理员可以删除任何订单
    order = get_order(session=session, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if order.is_deleted:
        raise HTTPException(status_code=400, detail="订单已被删除")
    
    # 软删除
    order.is_deleted = True
    order.deleted_at = datetime.utcnow()
    session.commit()
    
    return {"message": "订单已删除"}


# ==================== 支付相关接口 ====================

@router.post("/{order_id}/pay", response_model=OrderPublic)
def process_payment(
    order_id: UUID,
    payment_request: PaymentRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> Order:
    """处理支付（模拟支付成功）"""
    # 检查订单是否存在且属于当前用户
    order = get_order(session=session, order_id=order_id, user_id=current_user.id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise HTTPException(status_code=400, detail="订单状态不正确，无法支付")
    
    # 更新订单的支付方式
    order.payment_method = payment_request.payment_method.value
    order.payment_gateway_txn_id = payment_request.payment_gateway_txn_id
    session.add(order)
    session.commit()
    
    # 模拟支付成功，更新订单状态
    order = update_order_status(
        session=session,
        order_id=order_id,
        status=OrderStatus.PROCESSING,
        payment_gateway_txn_id=f"TXN_{order_id}_{int(datetime.utcnow().timestamp())}",
        user_id=current_user.id
    )
    
    return order


@router.post("/{order_id}/confirm-delivery", response_model=OrderPublic)
def confirm_delivery(
    order_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Order:
    """确认收货"""
    # 检查订单是否存在且属于当前用户
    order = get_order(session=session, order_id=order_id, user_id=current_user.id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if order.status != OrderStatus.SHIPPED:
        raise HTTPException(status_code=400, detail="订单状态不正确，无法确认收货")
    
    # 更新订单状态为已完成
    order = update_order_status(
        session=session,
        order_id=order_id,
        status=OrderStatus.COMPLETED,
        user_id=current_user.id
    )
    
    return order


# ==================== 取餐码相关接口 ====================

@router.post("/verify-pickup-code", response_model=OrderPublic)
def verify_pickup_code_endpoint(
    verify_request: VerifyPickupCodeRequest,
    session: SessionDep,
) -> Order:
    """商家核销取餐码"""
    order = verify_pickup_code(
        session=session, 
        pickup_code=verify_request.pickup_code
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="取餐码无效或订单状态不正确")
    
    return order


@router.get("/pickup-code/{pickup_code}", response_model=OrderPublic)
def get_order_by_pickup_code_endpoint(
    pickup_code: str,
    session: SessionDep,
) -> Order:
    """通过取餐码查询订单信息（商家查看）"""
    order = get_order_by_pickup_code(
        session=session, 
        pickup_code=pickup_code
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="取餐码不存在")
    
    return order
