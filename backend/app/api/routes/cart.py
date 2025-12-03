from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.crud_cart import (
    batch_delete_cart_items,
    batch_update_cart_items,
    clear_cart_by_user,
    create_cart_item,
    create_cart_item_simple,
    delete_cart_item,
    get_cart_items_with_details,
    get_cart_store_groups,
    get_cart_summary,
    get_cart_item,
    update_cart_item,
)
from app.models import (
    CartItem,
    CartItemCreate,
    CartItemPublic,
    CartItemSimpleCreate,
    CartItemUpdate,
    CartItemWithDetails,
    CartItemsPublic,
    CartPublic,
    CartStoreGroup,
    CartSummary,
    CartBatchUpdateRequest,
)

router = APIRouter()


# ==================== 购物车基础接口 ====================

@router.get("/", response_model=CartItemsPublic)
def get_my_cart(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    store_id: UUID = Query(None, description="按店铺过滤"),
    is_selected: bool = Query(None, description="按选中状态过滤"),
) -> CartItemsPublic:
    """获取我的购物车列表"""
    items, is_more = get_cart_items_with_details(
        session, 
        current_user.id, 
        skip=skip, 
        limit=limit,
        store_id=store_id,
        is_selected=is_selected
    )
    summary = get_cart_summary(session, current_user.id)
    
    return CartItemsPublic(
        data=items,
        count=len(items),
        is_more=is_more,
        summary=summary
    )


@router.get("/full", response_model=CartPublic)
def get_my_cart_full(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> CartPublic:
    """获取我的完整购物车信息（包含店铺分组）"""
    items, _ = get_cart_items_with_details(session, current_user.id, limit=1000)
    store_groups = get_cart_store_groups(session, current_user.id)
    summary = get_cart_summary(session, current_user.id)
    
    return CartPublic(
        items=items,
        store_groups=store_groups,
        summary=summary
    )


@router.get("/summary", response_model=CartSummary)
def get_cart_summary_info(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> CartSummary:
    """获取购物车汇总信息"""
    return get_cart_summary(session, current_user.id)


@router.get("/stores", response_model=List[CartStoreGroup])
def get_cart_store_groups_info(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> List[CartStoreGroup]:
    """获取按店铺分组的购物车"""
    return get_cart_store_groups(session, current_user.id)


@router.get("/{cart_item_id}", response_model=CartItemPublic)
def get_cart_item_by_id(
    cart_item_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> CartItem:
    """获取购物车项详情"""
    cart_item = get_cart_item(session, cart_item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    
    # 检查权限：只能查看自己的购物车项
    if cart_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此购物车项")
    
    return cart_item


@router.post("/", response_model=CartItemPublic)
def add_to_cart(
    request_data: dict,
    session: SessionDep,
    current_user: CurrentUser,
) -> CartItem:
    """添加商品到购物车 - 支持完整字段和简化字段"""
    try:
        # 检查是否只提供了product_id和quantity（简化模式）
        if "product_id" in request_data and "quantity" in request_data:
            if "store_id" not in request_data or "unit_price" not in request_data or "total_price" not in request_data:
                # 使用简化模式
                from app.models import CartItemSimpleCreate
                cart_item_simple = CartItemSimpleCreate(
                    product_id=request_data["product_id"],
                    quantity=request_data["quantity"],
                    product_spec=request_data.get("product_spec"),
                    notes=request_data.get("notes")
                )
                return create_cart_item_simple(session, cart_item_simple, current_user.id)
        
        # 否则使用完整模式
        cart_item = CartItemCreate(**request_data)
        return create_cart_item(session, cart_item, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/simple", response_model=CartItemPublic)
def add_to_cart_simple(
    cart_item: CartItemSimpleCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> CartItem:
    """简化添加商品到购物车（只需要商品ID和数量）"""
    try:
        return create_cart_item_simple(session, cart_item, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 批量操作接口 ====================

@router.put("/batch", response_model=List[CartItemPublic])
def batch_update_cart_items_endpoint(
    *,
    request: CartBatchUpdateRequest,
    session: SessionDep,
    current_user: CurrentUser,
) -> List[CartItem]:
    """批量更新购物车项"""
    # 将模型转换为字典列表
    updates = []
    for item in request.updates:
        update_dict = {
            "id": item.id,
        }
        if item.quantity is not None:
            update_dict["quantity"] = item.quantity
        if item.is_selected is not None:
            update_dict["is_selected"] = item.is_selected
        if item.product_spec is not None:
            update_dict["product_spec"] = item.product_spec
        if item.notes is not None:
            update_dict["notes"] = item.notes
        updates.append(update_dict)
    
    return batch_update_cart_items(session, current_user.id, updates)


@router.put("/{cart_item_id}", response_model=CartItemPublic)
def update_cart_item_by_id(
    cart_item_id: UUID,
    cart_item_update: CartItemUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> CartItem:
    """更新购物车项"""
    cart_item = get_cart_item(session, cart_item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    
    # 检查权限：只能更新自己的购物车项
    if cart_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此购物车项")
    
    updated_cart_item = update_cart_item(session, cart_item_id, cart_item_update)
    if not updated_cart_item:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    
    return updated_cart_item


@router.delete("/{cart_item_id}")
def delete_cart_item_by_id(
    cart_item_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """删除购物车项"""
    cart_item = get_cart_item(session, cart_item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    
    # 检查权限：只能删除自己的购物车项
    if cart_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此购物车项")
    
    success = delete_cart_item(session, cart_item_id)
    if not success:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    
    return {"message": "购物车项删除成功"}




@router.delete("/batch")
def batch_delete_cart_items_endpoint(
    *,
    cart_item_ids: List[UUID],
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """批量删除购物车项"""
    deleted_count = batch_delete_cart_items(session, current_user.id, cart_item_ids)
    return {"message": f"成功删除 {deleted_count} 个购物车项"}


@router.delete("/clear")
def clear_cart(
    *,
    store_id: UUID = Query(None, description="清空指定店铺的购物车"),
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """清空购物车"""
    deleted_count = clear_cart_by_user(session, current_user.id, store_id)
    if store_id:
        return {"message": f"成功清空指定店铺的购物车，删除了 {deleted_count} 个商品"}
    else:
        return {"message": f"成功清空购物车，删除了 {deleted_count} 个商品"}


# ==================== 快捷操作接口 ====================

@router.put("/{cart_item_id}/quantity")
def update_cart_item_quantity(
    cart_item_id: UUID,
    *,
    quantity: int = Query(..., ge=1, description="新的数量"),
    session: SessionDep,
    current_user: CurrentUser,
) -> CartItemPublic:
    """更新购物车项数量"""
    cart_item = get_cart_item(session, cart_item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    
    # 检查权限
    if cart_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此购物车项")
    
    cart_item_update = CartItemUpdate(quantity=quantity)
    updated_cart_item = update_cart_item(session, cart_item_id, cart_item_update)
    if not updated_cart_item:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    
    return updated_cart_item


@router.put("/{cart_item_id}/select")
def toggle_cart_item_selection(
    cart_item_id: UUID,
    *,
    is_selected: bool = Query(..., description="是否选中"),
    session: SessionDep,
    current_user: CurrentUser,
) -> CartItemPublic:
    """切换购物车项选中状态"""
    cart_item = get_cart_item(session, cart_item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    
    # 检查权限
    if cart_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此购物车项")
    
    cart_item_update = CartItemUpdate(is_selected=is_selected)
    updated_cart_item = update_cart_item(session, cart_item_id, cart_item_update)
    if not updated_cart_item:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    
    return updated_cart_item


@router.put("/select-all")
def select_all_cart_items(
    *,
    is_selected: bool = Query(..., description="是否全选"),
    store_id: UUID = Query(None, description="指定店铺"),
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """全选/取消全选购物车项"""
    # 获取需要更新的购物车项
    items, _ = get_cart_items_with_details(
        session, 
        current_user.id, 
        limit=1000,
        store_id=store_id
    )
    
    # 批量更新选中状态
    updates = []
    for item in items:
        updates.append({
            "id": item.id,
            "is_selected": is_selected
        })
    
    batch_update_cart_items(session, current_user.id, updates)
    
    action = "全选" if is_selected else "取消全选"
    scope = f"店铺 {store_id}" if store_id else "全部"
    return {"message": f"成功{action}{scope}购物车项"}


# ==================== 管理员接口 ====================

@router.get("/admin/user/{user_id}", response_model=List[CartItemPublic], dependencies=[Depends(get_current_active_superuser)])
def get_user_cart_admin(
    user_id: UUID,
    *,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> List[CartItem]:
    """获取指定用户的购物车（管理员）"""
    items, _ = get_cart_items_with_details(session, user_id, skip=skip, limit=limit)
    return [item for item in items]


@router.delete("/admin/user/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def clear_user_cart_admin(
    user_id: UUID,
    *,
    session: SessionDep,
) -> dict:
    """清空指定用户的购物车（管理员）"""
    deleted_count = clear_cart_by_user(session, user_id)
    return {"message": f"成功清空用户购物车，删除了 {deleted_count} 个商品"}
