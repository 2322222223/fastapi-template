from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.models import MembershipBenefit, MembershipBenefitCreate, MembershipBenefitUpdate


def create_membership_benefit(
    session: Session, membership_benefit: MembershipBenefitCreate
) -> MembershipBenefit:
    """创建会员权益"""
    db_membership_benefit = MembershipBenefit.model_validate(membership_benefit)
    session.add(db_membership_benefit)
    session.commit()
    session.refresh(db_membership_benefit)
    return db_membership_benefit


def get_membership_benefit(
    session: Session, membership_benefit_id: UUID
) -> Optional[MembershipBenefit]:
    """根据ID获取会员权益"""
    statement = select(MembershipBenefit).where(MembershipBenefit.id == membership_benefit_id)
    return session.exec(statement).first()


def get_membership_benefits_by_user(
    session: Session, user_id: UUID
) -> List[MembershipBenefit]:
    """获取用户的所有会员权益"""
    statement = select(MembershipBenefit).where(MembershipBenefit.user_id == user_id)
    return list(session.exec(statement).all())


def get_active_membership_benefits(
    session: Session, user_id: UUID
) -> List[MembershipBenefit]:
    """获取用户的有效会员权益"""
    statement = select(MembershipBenefit).where(
        MembershipBenefit.user_id == user_id,
        MembershipBenefit.status == "ACTIVE"
    )
    return list(session.exec(statement).all())


def get_membership_benefits_by_provider(
    session: Session, user_id: UUID, provider_id: str
) -> List[MembershipBenefit]:
    """获取用户指定平台的会员权益"""
    statement = select(MembershipBenefit).where(
        MembershipBenefit.user_id == user_id,
        MembershipBenefit.provider_id == provider_id
    )
    return list(session.exec(statement).all())


def update_membership_benefit(
    session: Session,
    membership_benefit_id: UUID,
    membership_benefit_update: MembershipBenefitUpdate,
) -> Optional[MembershipBenefit]:
    """更新会员权益"""
    db_membership_benefit = get_membership_benefit(session, membership_benefit_id)
    if not db_membership_benefit:
        return None
    
    data = membership_benefit_update.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(db_membership_benefit, key, value)
    
    session.add(db_membership_benefit)
    session.commit()
    session.refresh(db_membership_benefit)
    return db_membership_benefit


def delete_membership_benefit(
    session: Session, membership_benefit_id: UUID
) -> bool:
    """删除会员权益"""
    db_membership_benefit = get_membership_benefit(session, membership_benefit_id)
    if not db_membership_benefit:
        return False
    
    session.delete(db_membership_benefit)
    session.commit()
    return True


def update_membership_benefit_status(
    session: Session, membership_benefit_id: UUID, status: str
) -> Optional[MembershipBenefit]:
    """更新会员权益状态"""
    db_membership_benefit = get_membership_benefit(session, membership_benefit_id)
    if not db_membership_benefit:
        return None
    
    db_membership_benefit.status = status
    session.add(db_membership_benefit)
    session.commit()
    session.refresh(db_membership_benefit)
    return db_membership_benefit
