from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.crud_coupon import (
    create_coupon_template,
    create_user_coupon,
    delete_coupon_template,
    delete_user_coupon,
    get_available_user_coupons,
    get_coupon_template,
    get_coupon_templates,
    get_expired_user_coupons,
    get_used_user_coupons,
    get_user_coupon,
    get_user_coupon_stats,
    get_user_coupons_by_user,
    update_coupon_template,
    update_user_coupon,
    use_user_coupon,
)
from app.models import (
    CouponTemplate,
    CouponTemplateCreate,
    CouponTemplatePublic,
    CouponTemplateUpdate,
    CouponTemplatesPublic,
    UserCoupon,
    UserCouponCreate,
    UserCouponPublic,
    UserCouponUpdate,
    UserCouponsPublic,
    UserCouponsListPublic,
)

router = APIRouter()


# ==================== 优惠券模板管理接口 ====================

@router.get("/templates", response_model=CouponTemplatesPublic)
def get_coupon_templates_list(
    *,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: bool = Query(None, description="是否激活"),
) -> CouponTemplatesPublic:
    """获取优惠券模板列表"""
    templates = get_coupon_templates(session, skip=skip, limit=limit, is_active=is_active)
    return CouponTemplatesPublic(data=templates, count=len(templates))


@router.get("/templates/{template_id}", response_model=CouponTemplatePublic)
def get_coupon_template_by_id(
    template_id: UUID,
    session: SessionDep,
) -> CouponTemplate:
    """获取优惠券模板详情"""
    template = get_coupon_template(session, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="优惠券模板不存在")
    return template


@router.post("/templates", response_model=CouponTemplatePublic, dependencies=[Depends(get_current_active_superuser)])
def create_coupon_template_endpoint(
    template: CouponTemplateCreate,
    session: SessionDep,
) -> CouponTemplate:
    """创建优惠券模板（管理员）"""
    return create_coupon_template(session, template)


@router.put("/templates/{template_id}", response_model=CouponTemplatePublic, dependencies=[Depends(get_current_active_superuser)])
def update_coupon_template_endpoint(
    template_id: UUID,
    template_update: CouponTemplateUpdate,
    session: SessionDep,
) -> CouponTemplate:
    """更新优惠券模板（管理员）"""
    updated_template = update_coupon_template(session, template_id, template_update)
    if not updated_template:
        raise HTTPException(status_code=404, detail="优惠券模板不存在")
    return updated_template


@router.delete("/templates/{template_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_coupon_template_endpoint(
    template_id: UUID,
    session: SessionDep,
) -> dict:
    """删除优惠券模板（管理员）"""
    success = delete_coupon_template(session, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="优惠券模板不存在")
    return {"message": "优惠券模板删除成功"}


# ==================== 用户优惠券接口 ====================

@router.get("/my", response_model=UserCouponsPublic)
def get_my_coupons(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> UserCouponsPublic:
    """获取我的优惠券列表"""
    coupons = get_user_coupons_by_user(session, current_user.id, skip=skip, limit=limit)
    stats = get_user_coupon_stats(session, current_user.id)
    
    # 判断是否还有更多数据
    is_more = len(coupons) == limit
    
    return UserCouponsPublic(
        data=coupons,
        count=len(coupons),
        is_more=is_more,
        available_count=stats["available_count"],
        used_count=stats["used_count"],
        expired_count=stats["expired_count"]
    )


@router.get("/my/available", response_model=UserCouponsListPublic)
def get_my_available_coupons(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> UserCouponsListPublic:
    """获取我的可用优惠券（未使用且在有效期内）"""
    coupons, is_more = get_available_user_coupons(session, current_user.id, skip=skip, limit=limit)
    return UserCouponsListPublic(
        data=coupons,
        count=len(coupons),
        is_more=is_more
    )


@router.get("/my/used", response_model=UserCouponsListPublic)
def get_my_used_coupons(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> UserCouponsListPublic:
    """获取我的已使用优惠券"""
    coupons, is_more = get_used_user_coupons(session, current_user.id, skip=skip, limit=limit)
    return UserCouponsListPublic(
        data=coupons,
        count=len(coupons),
        is_more=is_more
    )


@router.get("/my/expired", response_model=UserCouponsListPublic)
def get_my_expired_coupons(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> UserCouponsListPublic:
    """获取我的已过期优惠券"""
    coupons, is_more = get_expired_user_coupons(session, current_user.id, skip=skip, limit=limit)
    return UserCouponsListPublic(
        data=coupons,
        count=len(coupons),
        is_more=is_more
    )


@router.get("/my/stats")
def get_my_coupon_stats(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """获取我的优惠券统计信息"""
    return get_user_coupon_stats(session, current_user.id)


@router.get("/{coupon_id}", response_model=UserCouponPublic)
def get_coupon_by_id(
    coupon_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> UserCoupon:
    """获取优惠券详情"""
    coupon = get_user_coupon(session, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    
    # 检查权限：只能查看自己的优惠券
    if coupon.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此优惠券")
    
    return coupon


@router.post("/claim", response_model=UserCouponPublic)
def claim_coupon(
    *,
    template_id: UUID = Query(..., description="优惠券模板ID"),
    session: SessionDep,
    current_user: CurrentUser,
) -> UserCoupon:
    """领取优惠券"""
    # 检查模板是否存在且激活
    template = get_coupon_template(session, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="优惠券模板不存在")
    
    if not template.is_active:
        raise HTTPException(status_code=400, detail="优惠券模板未激活")
    
    # 检查是否还有剩余数量
    if template.total_quantity != -1 and template.issued_quantity >= template.total_quantity:
        raise HTTPException(status_code=400, detail="优惠券已领完")
    
    # 创建用户优惠券
    user_coupon_create = UserCouponCreate(
        user_id=current_user.id,
        coupon_template_id=template_id
    )
    
    try:
        return create_user_coupon(session, user_coupon_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{coupon_id}", response_model=UserCouponPublic)
def update_coupon_by_id(
    coupon_id: UUID,
    coupon_update: UserCouponUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> UserCoupon:
    """更新优惠券信息"""
    coupon = get_user_coupon(session, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    
    # 检查权限：只能更新自己的优惠券
    if coupon.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此优惠券")
    
    updated_coupon = update_user_coupon(session, coupon_id, coupon_update)
    if not updated_coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    
    return updated_coupon


@router.put("/{coupon_id}/use", response_model=UserCouponPublic)
def use_coupon(
    coupon_id: UUID,
    *,
    order_id: UUID = Query(None, description="关联订单ID"),
    session: SessionDep,
    current_user: CurrentUser,
) -> UserCoupon:
    """使用优惠券"""
    coupon = get_user_coupon(session, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    
    # 检查权限：只能使用自己的优惠券
    if coupon.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权使用此优惠券")
    
    used_coupon = use_user_coupon(session, coupon_id, order_id)
    if not used_coupon:
        raise HTTPException(status_code=400, detail="优惠券不可用或已过期")
    
    return used_coupon


@router.delete("/{coupon_id}")
def delete_coupon_by_id(
    coupon_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """删除优惠券"""
    coupon = get_user_coupon(session, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    
    # 检查权限：只能删除自己的优惠券
    if coupon.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此优惠券")
    
    success = delete_user_coupon(session, coupon_id)
    if not success:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    
    return {"message": "优惠券删除成功"}


# ==================== 管理员接口 ====================

@router.get("/admin/all", response_model=List[UserCouponPublic], dependencies=[Depends(get_current_active_superuser)])
def get_all_coupons(
    *,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> List[UserCoupon]:
    """获取所有用户的优惠券（管理员）"""
    from sqlmodel import select
    statement = select(UserCoupon).offset(skip).limit(limit)
    return list(session.exec(statement).all())


@router.get("/admin/user/{user_id}", response_model=List[UserCouponPublic], dependencies=[Depends(get_current_active_superuser)])
def get_user_coupons_admin(
    user_id: UUID,
    *,
    session: SessionDep,
) -> List[UserCoupon]:
    """获取指定用户的所有优惠券（管理员）"""
    return get_user_coupons_by_user(session, user_id)
