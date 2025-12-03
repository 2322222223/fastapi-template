"""
邀请系统CRUD操作
"""
import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func

from app.models import (
    Invitation, InvitationCreate, InvitationUpdate, InvitationStatus,
    InvitationStats, User
)
from app.utils import generate_invite_code


def create_invitation(
    *, session: Session, invitation: InvitationCreate
) -> Invitation:
    """创建邀请记录"""
    try:
       
        
        new_id = uuid.uuid4()
        print(f"DEBUG CRUD: 生成的新ID = {new_id}")
        
        db_obj = Invitation(
            id=new_id,
            inviter_id=invitation.inviter_id,
            invitee_id=invitation.invitee_id,
            status=invitation.status,
            reward_points=invitation.reward_points,
            reward_claimed_at=invitation.reward_claimed_at
        )
        
        session.add(db_obj)
        
        session.commit()
        
        session.refresh(db_obj)
        
        return db_obj
    except Exception as e:
        print(f"ERROR CRUD: 异常信息: {str(e)}")
        raise e


def get_invitation_by_id(
    *, session: Session, invitation_id: uuid.UUID
) -> Optional[Invitation]:
    """根据ID获取邀请记录"""
    return session.get(Invitation, invitation_id)


def get_invitation_by_invitee(
    *, session: Session, invitee_id: uuid.UUID
) -> Optional[Invitation]:
    """根据被邀请人ID获取邀请记录"""
    query = select(Invitation).where(Invitation.invitee_id == invitee_id)
    result = session.exec(query).first()
    
    if result is None:
        return None
    
    # 处理可能的 Row 对象
    if hasattr(result, 'id'):
        return result
    elif hasattr(result, '_asdict'):
        row_data = result._asdict()
        if 'Invitation' in row_data:
            return row_data['Invitation']
        else:
            invitation_id = row_data.get('id')
            if invitation_id:
                return session.get(Invitation, invitation_id)
    
    return None


def get_invitations_by_inviter(
    *, session: Session, inviter_id: uuid.UUID, 
    skip: int = 0, limit: int = 100
) -> Tuple[List[Invitation], int]:
    """获取邀请人的所有邀请记录"""
    # 查询邀请记录
    query = select(Invitation).where(
        Invitation.inviter_id == inviter_id
    ).order_by(Invitation.created_at.desc()).offset(skip).limit(limit)
    
    results = session.exec(query).all()
    
    # 处理可能的 Row 对象
    invitations = []
    for result in results:
        if hasattr(result, 'id'):
            # 直接是 Invitation 对象
            invitations.append(result)
        elif hasattr(result, '_asdict'):
            # 是 Row 对象，提取 Invitation 对象
            row_data = result._asdict()
            if 'Invitation' in row_data:
                invitations.append(row_data['Invitation'])
            else:
                # 如果结构不同，尝试重新查询
                invitation_id = row_data.get('id')
                if invitation_id:
                    invitation = session.get(Invitation, invitation_id)
                    if invitation:
                        invitations.append(invitation)
    
    # 查询总数
    count_query = select(func.count(Invitation.id)).where(
        Invitation.inviter_id == inviter_id
    )
    total = session.exec(count_query).scalar() or 0
    
    return invitations, total


def update_invitation(
    *, session: Session, invitation_id: uuid.UUID, 
    invitation_update: InvitationUpdate
) -> Optional[Invitation]:
    """更新邀请记录"""
    invitation = session.get(Invitation, invitation_id)
    if not invitation:
        return None
    
    # 更新字段
    update_data = invitation_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invitation, field, value)
    
    invitation.updated_at = datetime.utcnow()
    session.add(invitation)
    session.commit()
    session.refresh(invitation)
    return invitation


def get_invitation_stats(
    *, session: Session, user_id: uuid.UUID
) -> InvitationStats:
    """获取用户邀请统计"""
    # 总邀请数
    total_query = select(func.count(Invitation.id)).where(
        Invitation.inviter_id == user_id
    )
    total_invitations = session.exec(total_query).scalar() or 0
    
    # 已完成邀请数
    completed_query = select(func.count(Invitation.id)).where(
        and_(
            Invitation.inviter_id == user_id,
            Invitation.status == InvitationStatus.COMPLETED
        )
    )
    completed_invitations = session.exec(completed_query).scalar() or 0
    
    # 待处理邀请数
    pending_query = select(func.count(Invitation.id)).where(
        and_(
            Invitation.inviter_id == user_id,
            Invitation.status == InvitationStatus.PENDING
        )
    )
    pending_invitations = session.exec(pending_query).scalar() or 0
    
    # 总奖励积分
    total_reward_query = select(func.sum(Invitation.reward_points)).where(
        Invitation.inviter_id == user_id
    )
    total_reward_points = session.exec(total_reward_query).scalar() or 0
    
    # 已领取奖励积分
    claimed_reward_query = select(func.sum(Invitation.reward_points)).where(
        and_(
            Invitation.inviter_id == user_id,
            Invitation.reward_claimed_at.isnot(None)
        )
    )
    claimed_reward_points = session.exec(claimed_reward_query).scalar() or 0
    
    return InvitationStats(
        total_invitations=total_invitations,
        completed_invitations=completed_invitations,
        pending_invitations=pending_invitations,
        total_reward_points=total_reward_points,
        claimed_reward_points=claimed_reward_points
    )


def get_user_by_invite_code(
    *, session: Session, invite_code: str
) -> Optional[User]:
    """根据邀请码获取用户"""
    from sqlalchemy.orm import sessionmaker
    statement = select(User).where(User.invite_code == invite_code)
    user = session.exec(statement).first()
    
    print(f"DEBUG CRUD: get_user_by_invite_code 结果:")
    print(f"DEBUG CRUD: invite_code = {invite_code}")
    print(f"DEBUG CRUD: user = {user}")
    print(f"DEBUG CRUD: user type = {type(user)}")
    
    if user is None:
        print(f"DEBUG CRUD: 未找到邀请码对应的用户")
        return None
    
    # 确保返回的是 User 对象
    if hasattr(user, 'id'):
        print(f"DEBUG CRUD: user.id = {user.id}")
        return user
    else:
        print(f"DEBUG CRUD: 返回的对象没有 id 属性，尝试转换")
        # 如果是 Row 对象，尝试转换为 User
        try:
            if hasattr(user, '_asdict'):
                user_data = user._asdict()
                print(f"DEBUG CRUD: Row 数据: {user_data}")
                # Row 数据结构是 {'User': User对象}，直接提取 User 对象
                if 'User' in user_data:
                    actual_user = user_data['User']
                    print(f"DEBUG CRUD: 提取到的实际 User 对象: {actual_user}")
                    print(f"DEBUG CRUD: actual_user.id = {actual_user.id}")
                    return actual_user
                else:
                    # 如果结构不同，尝试通过 ID 重新查询
                    user_id = user_data.get('id')
                    if user_id:
                        user_obj = session.get(User, user_id)
                        print(f"DEBUG CRUD: 重新查询得到的 user_obj = {user_obj}")
                        return user_obj
        except Exception as e:
            print(f"DEBUG CRUD: 转换失败: {e}")
        return None


def generate_unique_invite_code(*, session: Session, max_attempts: int = 10) -> str:
    """生成唯一的邀请码"""
    for _ in range(max_attempts):
        invite_code = generate_invite_code()
        # 检查邀请码是否已存在
        existing_user = get_user_by_invite_code(session=session, invite_code=invite_code)
        if not existing_user:
            return invite_code
    
    # 如果多次尝试后仍有冲突，使用UUID作为后缀
    base_code = generate_invite_code(length=6)
    unique_suffix = str(uuid.uuid4())[:2].upper()
    return f"{base_code}{unique_suffix}"
