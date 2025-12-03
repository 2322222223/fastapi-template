from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.crud_membership_benefit import (
    create_membership_benefit,
    delete_membership_benefit,
    get_active_membership_benefits,
    get_membership_benefit,
    get_membership_benefits_by_provider,
    get_membership_benefits_by_user,
    update_membership_benefit,
    update_membership_benefit_status,
)
from app.models import (
    MembershipBenefit,
    MembershipBenefitCreate,
    MembershipBenefitPublic,
    MembershipBenefitUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[MembershipBenefitPublic])
def get_membership_benefits(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    provider_id: str = Query(None, description="平台ID过滤"),
    active_only: bool = Query(False, description="只返回有效权益"),
) -> List[MembershipBenefit]:
    """获取当前用户的会员权益列表"""
    if active_only:
        membership_benefits = get_active_membership_benefits(session, current_user.id)
    elif provider_id:
        membership_benefits = get_membership_benefits_by_provider(
            session, current_user.id, provider_id
        )
    else:
        membership_benefits = get_membership_benefits_by_user(session, current_user.id)
    
    return membership_benefits


@router.get("/{membership_benefit_id}", response_model=MembershipBenefitPublic)
def get_membership_benefit_by_id(
    membership_benefit_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> MembershipBenefit:
    """获取指定会员权益详情"""
    membership_benefit = get_membership_benefit(session, membership_benefit_id)
    if not membership_benefit:
        raise HTTPException(status_code=404, detail="会员权益不存在")
    
    # 检查权限：只能查看自己的权益
    if membership_benefit.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此会员权益")
    
    return membership_benefit


@router.post("/", response_model=MembershipBenefitPublic)
def create_new_membership_benefit(
    membership_benefit: MembershipBenefitCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> MembershipBenefit:
    """创建新的会员权益"""
    # 设置用户ID为当前用户
    membership_benefit.user_id = current_user.id
    return create_membership_benefit(session, membership_benefit)


@router.put("/{membership_benefit_id}", response_model=MembershipBenefitPublic)
def update_membership_benefit_by_id(
    membership_benefit_id: UUID,
    membership_benefit_update: MembershipBenefitUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> MembershipBenefit:
    """更新会员权益信息"""
    membership_benefit = get_membership_benefit(session, membership_benefit_id)
    if not membership_benefit:
        raise HTTPException(status_code=404, detail="会员权益不存在")
    
    # 检查权限：只能更新自己的权益
    if membership_benefit.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此会员权益")
    
    updated_membership_benefit = update_membership_benefit(
        session, membership_benefit_id, membership_benefit_update
    )
    if not updated_membership_benefit:
        raise HTTPException(status_code=404, detail="会员权益不存在")
    
    return updated_membership_benefit


@router.put("/{membership_benefit_id}/status", response_model=MembershipBenefitPublic)
def update_membership_benefit_status_by_id(
    membership_benefit_id: UUID,
    *,
    status: str = Query(..., description="新状态：ACTIVE, EXPIRED"),
    session: SessionDep,
    current_user: CurrentUser,
) -> MembershipBenefit:
    """更新会员权益状态"""
    membership_benefit = get_membership_benefit(session, membership_benefit_id)
    if not membership_benefit:
        raise HTTPException(status_code=404, detail="会员权益不存在")
    
    # 检查权限：只能更新自己的权益
    if membership_benefit.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此会员权益")
    
    if status not in ["ACTIVE", "EXPIRED"]:
        raise HTTPException(status_code=400, detail="状态值无效")
    
    updated_membership_benefit = update_membership_benefit_status(
        session, membership_benefit_id, status
    )
    if not updated_membership_benefit:
        raise HTTPException(status_code=404, detail="会员权益不存在")
    
    return updated_membership_benefit


@router.delete("/{membership_benefit_id}")
def delete_membership_benefit_by_id(
    membership_benefit_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """删除会员权益"""
    membership_benefit = get_membership_benefit(session, membership_benefit_id)
    if not membership_benefit:
        raise HTTPException(status_code=404, detail="会员权益不存在")
    
    # 检查权限：只能删除自己的权益
    if membership_benefit.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此会员权益")
    
    success = delete_membership_benefit(session, membership_benefit_id)
    if not success:
        raise HTTPException(status_code=404, detail="会员权益不存在")
    
    return {"message": "会员权益删除成功"}


# 管理员接口
@router.get("/admin/all", response_model=List[MembershipBenefitPublic], dependencies=[Depends(get_current_active_superuser)])
def get_all_membership_benefits(
    *,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> List[MembershipBenefit]:
    """获取所有用户的会员权益（管理员）"""
    from sqlmodel import select
    statement = select(MembershipBenefit).offset(skip).limit(limit)
    return list(session.exec(statement).all())


@router.get("/admin/user/{user_id}", response_model=List[MembershipBenefitPublic], dependencies=[Depends(get_current_active_superuser)])
def get_user_membership_benefits_admin(
    user_id: UUID,
    *,
    session: SessionDep,
) -> List[MembershipBenefit]:
    """获取指定用户的所有会员权益（管理员）"""
    return get_membership_benefits_by_user(session, user_id)
