from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select, and_, or_

from app.models import (
    CouponTemplate,
    CouponTemplateCreate,
    CouponTemplateUpdate,
    UserCoupon,
    UserCouponCreate,
    UserCouponUpdate,
)


# ==================== 优惠券模板 CRUD ====================

def create_coupon_template(session: Session, coupon_template: CouponTemplateCreate) -> CouponTemplate:
    """创建优惠券模板"""
    db_coupon_template = CouponTemplate.model_validate(coupon_template)
    session.add(db_coupon_template)
    session.commit()
    session.refresh(db_coupon_template)
    return db_coupon_template


def get_coupon_template(session: Session, template_id: UUID) -> Optional[CouponTemplate]:
    """获取优惠券模板"""
    statement = select(CouponTemplate).where(CouponTemplate.id == template_id)
    return session.exec(statement).first()


def get_coupon_templates(
    session: Session, 
    skip: int = 0, 
    limit: int = 100,
    is_active: Optional[bool] = None
) -> List[CouponTemplate]:
    """获取优惠券模板列表"""
    statement = select(CouponTemplate)
    
    if is_active is not None:
        statement = statement.where(CouponTemplate.is_active == is_active)
    
    statement = statement.offset(skip).limit(limit)
    return list(session.exec(statement).all())


def update_coupon_template(
    session: Session, 
    template_id: UUID, 
    coupon_template_update: CouponTemplateUpdate
) -> Optional[CouponTemplate]:
    """更新优惠券模板"""
    db_coupon_template = get_coupon_template(session, template_id)
    if not db_coupon_template:
        return None
    
    update_data = coupon_template_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_coupon_template, field, value)
    
    db_coupon_template.updated_at = datetime.utcnow()
    session.add(db_coupon_template)
    session.commit()
    session.refresh(db_coupon_template)
    return db_coupon_template


def delete_coupon_template(session: Session, template_id: UUID) -> bool:
    """删除优惠券模板"""
    db_coupon_template = get_coupon_template(session, template_id)
    if not db_coupon_template:
        return False
    
    session.delete(db_coupon_template)
    session.commit()
    return True


# ==================== 用户优惠券 CRUD ====================

def create_user_coupon(session: Session, user_coupon: UserCouponCreate) -> UserCoupon:
    """创建用户优惠券"""
    # 从模板复制信息
    template = get_coupon_template(session, user_coupon.coupon_template_id)
    if not template:
        raise ValueError("优惠券模板不存在")
    
    # 计算有效期
    now = datetime.utcnow()
    if template.validity_type == 1:  # 固定日期
        start_time = template.fixed_start_time or now
        end_time = template.fixed_end_time or now
    else:  # 领取后X天有效
        start_time = now
        end_time = datetime(now.year, now.month, now.day + template.valid_days, 23, 59, 59)
    
    # 创建用户优惠券
    db_user_coupon = UserCoupon(
        user_id=user_coupon.user_id,
        coupon_template_id=user_coupon.coupon_template_id,
        title=template.title,
        coupon_type=template.coupon_type,
        value=template.value,
        min_spend=template.min_spend,
        description=template.description,
        usage_scope_desc=template.usage_scope_desc,
        start_time=start_time,
        end_time=end_time,
        order_id=user_coupon.order_id,
        coupon_code=user_coupon.coupon_code
    )
    
    session.add(db_user_coupon)
    
    # 更新模板的已领取数量
    template.issued_quantity += 1
    session.add(template)
    
    session.commit()
    session.refresh(db_user_coupon)
    return db_user_coupon


def get_user_coupon(session: Session, coupon_id: UUID) -> Optional[UserCoupon]:
    """获取用户优惠券"""
    statement = select(UserCoupon).where(UserCoupon.id == coupon_id)
    return session.exec(statement).first()


def get_user_coupons_by_user(
    session: Session, 
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> List[UserCoupon]:
    """获取用户的所有优惠券"""
    statement = select(UserCoupon).where(UserCoupon.user_id == user_id)
    statement = statement.offset(skip).limit(limit).order_by(UserCoupon.created_at.desc())
    return list(session.exec(statement).all())


def get_user_coupons_by_status(
    session: Session,
    user_id: UUID,
    status: int,
    skip: int = 0,
    limit: int = 100
) -> List[UserCoupon]:
    """根据状态获取用户优惠券"""
    statement = select(UserCoupon).where(
        and_(UserCoupon.user_id == user_id, UserCoupon.status == status)
    )
    statement = statement.offset(skip).limit(limit).order_by(UserCoupon.created_at.desc())
    return list(session.exec(statement).all())


def get_available_user_coupons(
    session: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[UserCoupon], bool]:
    """获取用户可用优惠券（未使用且在有效期内）"""
    now = datetime.utcnow()
    statement = select(UserCoupon).where(
        and_(
            UserCoupon.user_id == user_id,
            UserCoupon.status == 0,  # 未使用
            UserCoupon.end_time > now  # 未过期
        )
    )
    statement = statement.offset(skip).limit(limit + 1).order_by(UserCoupon.created_at.desc())
    coupons = list(session.exec(statement).all())
    
    # 判断是否还有更多数据
    is_more = len(coupons) > limit
    if is_more:
        coupons = coupons[:limit]  # 只返回limit数量的数据
    
    return coupons, is_more


def get_expired_user_coupons(
    session: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[UserCoupon], bool]:
    """获取用户已过期优惠券（已过期但未使用）"""
    now = datetime.utcnow()
    statement = select(UserCoupon).where(
        and_(
            UserCoupon.user_id == user_id,
            UserCoupon.status.in_([0, 2]),  # 未使用或已过期状态
            UserCoupon.end_time <= now  # 已过期
        )
    )
    statement = statement.offset(skip).limit(limit + 1).order_by(UserCoupon.created_at.desc())
    coupons = list(session.exec(statement).all())
    
    # 判断是否还有更多数据
    is_more = len(coupons) > limit
    if is_more:
        coupons = coupons[:limit]  # 只返回limit数量的数据
    
    return coupons, is_more


def get_used_user_coupons(
    session: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[UserCoupon], bool]:
    """获取用户已使用优惠券"""
    statement = select(UserCoupon).where(
        and_(UserCoupon.user_id == user_id, UserCoupon.status == 1)
    )
    statement = statement.offset(skip).limit(limit + 1).order_by(UserCoupon.created_at.desc())
    coupons = list(session.exec(statement).all())
    
    # 判断是否还有更多数据
    is_more = len(coupons) > limit
    if is_more:
        coupons = coupons[:limit]  # 只返回limit数量的数据
    
    return coupons, is_more


def update_user_coupon(
    session: Session,
    coupon_id: UUID,
    user_coupon_update: UserCouponUpdate
) -> Optional[UserCoupon]:
    """更新用户优惠券"""
    db_user_coupon = get_user_coupon(session, coupon_id)
    if not db_user_coupon:
        return None
    
    update_data = user_coupon_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user_coupon, field, value)
    
    db_user_coupon.updated_at = datetime.utcnow()
    session.add(db_user_coupon)
    session.commit()
    session.refresh(db_user_coupon)
    return db_user_coupon


def use_user_coupon(
    session: Session,
    coupon_id: UUID,
    order_id: Optional[UUID] = None
) -> Optional[UserCoupon]:
    """使用优惠券"""
    db_user_coupon = get_user_coupon(session, coupon_id)
    if not db_user_coupon:
        return None
    
    # 检查优惠券是否可用
    now = datetime.utcnow()
    if db_user_coupon.status != 0 or db_user_coupon.end_time <= now:
        return None
    
    # 更新状态为已使用
    db_user_coupon.status = 1
    db_user_coupon.used_time = now
    if order_id:
        db_user_coupon.order_id = order_id
    
    db_user_coupon.updated_at = now
    session.add(db_user_coupon)
    session.commit()
    session.refresh(db_user_coupon)
    return db_user_coupon


def delete_user_coupon(session: Session, coupon_id: UUID) -> bool:
    """删除用户优惠券"""
    db_user_coupon = get_user_coupon(session, coupon_id)
    if not db_user_coupon:
        return False
    
    session.delete(db_user_coupon)
    session.commit()
    return True


def get_user_coupon_stats(session: Session, user_id: UUID) -> dict:
    """获取用户优惠券统计信息"""
    now = datetime.utcnow()
    
    # 总优惠券数
    total_statement = select(UserCoupon).where(UserCoupon.user_id == user_id)
    total_coupons = len(list(session.exec(total_statement).all()))
    
    # 可用优惠券数（未使用且在有效期内）
    available_statement = select(UserCoupon).where(
        and_(
            UserCoupon.user_id == user_id,
            UserCoupon.status == 0,
            UserCoupon.end_time > now
        )
    )
    available_coupons = len(list(session.exec(available_statement).all()))
    
    # 已使用优惠券数
    used_statement = select(UserCoupon).where(
        and_(UserCoupon.user_id == user_id, UserCoupon.status == 1)
    )
    used_coupons = len(list(session.exec(used_statement).all()))
    
    # 已过期优惠券数（已过期但未使用）
    expired_statement = select(UserCoupon).where(
        and_(
            UserCoupon.user_id == user_id,
            UserCoupon.status.in_([0, 2]),  # 未使用或已过期状态
            UserCoupon.end_time <= now
        )
    )
    expired_coupons = len(list(session.exec(expired_statement).all()))
    
    return {
        "total_count": total_coupons,
        "available_count": available_coupons,
        "used_count": used_coupons,
        "expired_count": expired_coupons
    }
