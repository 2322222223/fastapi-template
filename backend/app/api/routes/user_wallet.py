from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.crud_data_package import get_data_packages_by_user
from app.crud_membership_benefit import get_membership_benefits_by_user
from app.models import DataPackage, MembershipBenefit, User

router = APIRouter()


class UserWalletResponse:
    """用户钱包响应模型"""
    def __init__(
        self,
        user_id: UUID,
        phone: str,
        data_packages: List[DataPackage],
        membership_benefits: List[MembershipBenefit],
    ):
        self.user_id = user_id
        self.phone = phone
        self.data_packages = data_packages
        self.membership_benefits = membership_benefits


@router.get("/my-wallet")
def get_my_wallet(
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """获取当前用户的完整钱包信息（包括手机号、流量包、会员权益）"""
    # 获取用户的流量包
    data_packages = get_data_packages_by_user(session, current_user.id)
    
    # 获取用户的会员权益
    membership_benefits = get_membership_benefits_by_user(session, current_user.id)
    
    return {
        "user_id": current_user.id,
        "phone": current_user.phone,
        "data_packages": [
            {
                "id": str(pkg.id),
                "package_name": pkg.package_name,
                "package_type": pkg.package_type,
                "total_mb": pkg.total_mb,
                "used_mb": pkg.used_mb,
                "remaining_mb": pkg.total_mb - pkg.used_mb,
                "usage_percentage": round((pkg.used_mb / pkg.total_mb) * 100, 1) if pkg.total_mb > 0 else 0,
                "expiration_date": pkg.expiration_date.isoformat(),
                "is_shared": pkg.is_shared,
                "status": pkg.status,
                "created_at": pkg.created_at.isoformat(),
            }
            for pkg in data_packages
        ],
        "membership_benefits": [
            {
                "id": str(benefit.id),
                "benefit_name": benefit.benefit_name,
                "provider_id": benefit.provider_id,
                "description": benefit.description,
                "total_duration_days": benefit.total_duration_days,
                "activation_date": benefit.activation_date.isoformat(),
                "expiration_date": benefit.expiration_date.isoformat(),
                "status": benefit.status,
                "ui_config_json": benefit.ui_config_json,
                "created_at": benefit.created_at.isoformat(),
            }
            for benefit in membership_benefits
        ],
    }


@router.get("/user/{user_id}/wallet", dependencies=[Depends(get_current_active_superuser)])
def get_user_wallet(
    user_id: UUID,
    *,
    session: SessionDep,
) -> dict:
    """获取指定用户的完整钱包信息（管理员）"""
    # 获取用户信息
    from sqlmodel import select
    statement = select(User).where(User.id == user_id)
    user = session.exec(statement).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 获取用户的流量包
    data_packages = get_data_packages_by_user(session, user_id)
    
    # 获取用户的会员权益
    membership_benefits = get_membership_benefits_by_user(session, user_id)
    
    return {
        "user_id": str(user_id),
        "phone": user.phone,
        "email": user.email,
        "full_name": user.full_name,
        "data_packages": [
            {
                "id": str(pkg.id),
                "package_name": pkg.package_name,
                "package_type": pkg.package_type,
                "total_mb": pkg.total_mb,
                "used_mb": pkg.used_mb,
                "remaining_mb": pkg.total_mb - pkg.used_mb,
                "usage_percentage": round((pkg.used_mb / pkg.total_mb) * 100, 1) if pkg.total_mb > 0 else 0,
                "expiration_date": pkg.expiration_date.isoformat(),
                "is_shared": pkg.is_shared,
                "status": pkg.status,
                "created_at": pkg.created_at.isoformat(),
            }
            for pkg in data_packages
        ],
        "membership_benefits": [
            {
                "id": str(benefit.id),
                "benefit_name": benefit.benefit_name,
                "provider_id": benefit.provider_id,
                "description": benefit.description,
                "total_duration_days": benefit.total_duration_days,
                "activation_date": benefit.activation_date.isoformat(),
                "expiration_date": benefit.expiration_date.isoformat(),
                "status": benefit.status,
                "ui_config_json": benefit.ui_config_json,
                "created_at": benefit.created_at.isoformat(),
            }
            for benefit in membership_benefits
        ],
    }
