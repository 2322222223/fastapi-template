"""
邀请系统业务逻辑服务
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import (
    User, Invitation, InvitationCreate, InvitationUpdate, InvitationStatus,
    UserCreate, PointsSourceType
)
from app.crud import create_user
from app.crud_invitation import (
    create_invitation, get_invitation_by_id, get_invitation_by_invitee,
    get_user_by_invite_code, update_invitation
)
from app.crud_points import (
    get_user_points_balance, update_user_points_balance, create_points_transaction
)
from app.models import PointsTransactionCreate


class InvitationService:
    """邀请系统业务逻辑服务"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def register_with_invite(
        self, email: str, password: str, full_name: Optional[str], invite_code: str
    ) -> Dict[str, Any]:
        """
        使用邀请码注册新用户
        
        Args:
            email: 用户邮箱
            password: 用户密码
            full_name: 用户姓名
            invite_code: 邀请码
            
        Returns:
            注册结果
        """
        try:
            # 1. 验证邀请码是否有效
            inviter = get_user_by_invite_code(session=self.session, invite_code=invite_code)
            if not inviter:
                return {
                    "success": False,
                    "message": "邀请码无效或不存在",
                    "data": None
                }
            
            # 2. 检查邮箱是否已存在
            from app.crud import get_user_by_email
            existing_user = get_user_by_email(session=self.session, email=email)
            if existing_user:
                return {
                    "success": False,
                    "message": "该邮箱已被注册",
                    "data": None
                }
            
            # 3. 创建新用户
            user_create = UserCreate(
                email=email,
                password=password,
                full_name=full_name
            )
            new_user = create_user(session=self.session, user_create=user_create)
            
            # 4. 创建邀请关系记录
            invitation = InvitationCreate(
                inviter_id=inviter.id,
                invitee_id=new_user.id,
                reward_points=50  # 邀请奖励50积分
            )
            invitation_record = create_invitation(session=self.session, invitation=invitation)
            
            # 5. 给邀请人发放奖励积分
            inviter_balance = get_user_points_balance(session=self.session, user_id=inviter.id)
            new_inviter_balance = inviter_balance + invitation_record.reward_points
            update_user_points_balance(
                session=self.session, 
                user_id=inviter.id, 
                new_balance=new_inviter_balance
            )
            
            # 6. 创建邀请人积分流水记录
            inviter_transaction = PointsTransactionCreate(
                user_id=inviter.id,
                points_change=invitation_record.reward_points,
                balance_after=new_inviter_balance,
                source_type=PointsSourceType.INVITATION,
                source_id=str(invitation_record.id),
                description=f"邀请好友奖励：{new_user.full_name or new_user.email}"
            )
            create_points_transaction(session=self.session, points_transaction=inviter_transaction)
            
            # 7. 给被邀请人发放新用户奖励积分
            invitee_balance = get_user_points_balance(session=self.session, user_id=new_user.id)
            new_invitee_balance = invitee_balance + 20  # 新用户奖励20积分
            update_user_points_balance(
                session=self.session, 
                user_id=new_user.id, 
                new_balance=new_invitee_balance
            )
            
            # 8. 创建被邀请人积分流水记录
            invitee_transaction = PointsTransactionCreate(
                user_id=new_user.id,
                points_change=20,
                balance_after=new_invitee_balance,
                source_type=PointsSourceType.NEW_USER_BONUS,
                source_id=str(invitation_record.id),
                description="新用户注册奖励"
            )
            create_points_transaction(session=self.session, points_transaction=invitee_transaction)
            
            # 9. 更新邀请状态为已完成
            invitation_update = InvitationUpdate(
                status=InvitationStatus.COMPLETED,
                reward_claimed_at=datetime.utcnow()
            )
            update_invitation(
                session=self.session,
                invitation_id=invitation_record.id,
                invitation_update=invitation_update
            )
            
            return {
                "success": True,
                "message": "注册成功！您和邀请人都获得了积分奖励",
                "data": {
                    "user_id": str(new_user.id),
                    "inviter_reward": invitation_record.reward_points,
                    "new_user_reward": 20
                }
            }
            
        except IntegrityError as e:
            return {
                "success": False,
                "message": "注册失败，请重试",
                "data": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"注册失败：{str(e)}",
                "data": None
            }
    
    def register_with_invite_by_phone(
        self, phone: str, verification_code: str, full_name: Optional[str], invite_code: str
    ) -> Dict[str, Any]:
        """
        使用邀请码和手机号注册新用户
        
        Args:
            phone: 用户手机号
            verification_code: 验证码
            full_name: 用户姓名
            invite_code: 邀请码
            
        Returns:
            注册结果
        """
        try:
            # 1. 验证验证码
            if verification_code != "222223":
                return {
                    "success": False,
                    "message": "验证码错误",
                    "data": None
                }
            
            # 2. 验证邀请码是否有效
            inviter = get_user_by_invite_code(session=self.session, invite_code=invite_code)
            if not inviter:
                return {
                    "success": False,
                    "message": "邀请码无效或不存在",
                    "data": None
                }
            
            # 3. 检查手机号是否已存在
            from app.crud import get_user_by_phone
            existing_user = get_user_by_phone(session=self.session, phone=phone)
            if existing_user:
                return {
                    "success": False,
                    "message": "该手机号已被注册",
                    "data": None
                }
            
            # 4. 使用手机号创建新用户
            from app.crud import create_user_by_phone
            try:
                new_user = create_user_by_phone(
                    session=self.session, 
                    phone=phone, 
                    full_name=full_name
                )
            except Exception as e:
                return {
                    "success": False,
                    "message": f"创建用户失败：{str(e)}",
                    "data": None
                }
            
            # 5. 创建邀请关系记录
            try:
                print(f"DEBUG: 开始创建邀请记录")
                print(f"DEBUG: inviter.id = {inviter.id}, type = {type(inviter.id)}")
                print(f"DEBUG: new_user.id = {new_user.id}, type = {type(new_user.id)}")
                
                invitation = InvitationCreate(
                    inviter_id=inviter.id,
                    invitee_id=new_user.id,
                    reward_points=150  # 邀请奖励150积分
                )
                print(f"DEBUG: InvitationCreate 对象创建成功")
                print(f"DEBUG: invitation = {invitation}")
                
                invitation_record = create_invitation(session=self.session, invitation=invitation)
                print(f"DEBUG: create_invitation 调用成功")
                print(f"DEBUG: invitation_record.id = {invitation_record.id}")
            except Exception as e:
                print(f"ERROR: 异常信息: {str(e)}")
                return {
                    "success": False,
                    "message": f"创建邀请记录失败：{str(e)}",
                    "data": {"traceback": error_traceback}
                }
            
            return {
                "success": True,
                "message": "注册成功！",
                "data": {
                    "user_id": str(new_user.id),
                    "phone": phone,
                    "invitation_id": str(invitation_record.id)
                }
            }
            
        except IntegrityError as e:
            return {
                "success": False,
                "message": "注册失败，请重试",
                "data": None
            }
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return {
                "success": False,
                "message": f"注册失败：{str(e)}",
                "data": {"error_details": error_details}
            }
    
    def claim_invitation_reward(
        self, invitation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        领取邀请奖励（如果奖励机制需要手动领取）
        
        Args:
            invitation_id: 邀请记录ID
            user_id: 用户ID
            
        Returns:
            领取结果
        """
        try:
            # 获取邀请记录
            invitation = get_invitation_by_id(session=self.session, invitation_id=invitation_id)
            if not invitation:
                return {
                    "success": False,
                    "message": "邀请记录不存在",
                    "data": None
                }
            
            # 检查权限
            if invitation.inviter_id != user_id:
                return {
                    "success": False,
                    "message": "无权限领取此奖励",
                    "data": None
                }
            
            # 检查是否已领取
            if invitation.reward_claimed_at:
                return {
                    "success": False,
                    "message": "奖励已领取",
                    "data": None
                }
            
            # 检查邀请状态
            if invitation.status != InvitationStatus.COMPLETED:
                return {
                    "success": False,
                    "message": "邀请尚未完成，无法领取奖励",
                    "data": None
                }
            
            # 更新邀请记录
            invitation_update = InvitationUpdate(
                reward_claimed_at=datetime.utcnow()
            )
            updated_invitation = update_invitation(
                session=self.session,
                invitation_id=invitation_id,
                invitation_update=invitation_update
            )
            
            return {
                "success": True,
                "message": "奖励领取成功",
                "data": updated_invitation
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"领取失败：{str(e)}",
                "data": None
            }
    
    def get_invitation_info(self, invite_code: str) -> Dict[str, Any]:
        """
        获取邀请码信息
        
        Args:
            invite_code: 邀请码
            
        Returns:
            邀请码信息
        """
        user = get_user_by_invite_code(session=self.session, invite_code=invite_code)
        
        if not user:
            return {
                "success": False,
                "message": "邀请码无效",
                "data": None
            }
        
        return {
            "success": True,
            "message": "邀请码有效",
            "data": {
                "inviter_name": user.full_name or "匿名用户",
                "inviter_email": user.email,
                "invite_code": invite_code
            }
        }


def create_invitation_service(session: Session) -> InvitationService:
    """创建邀请服务实例"""
    return InvitationService(session)
