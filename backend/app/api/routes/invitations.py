"""
邀请系统API路由
"""
import uuid
from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.models import User, InvitationStatus, InvitationStats
from app.crud_invitation import (
    create_invitation, get_invitations_by_inviter, get_invitation_stats,
    get_user_by_invite_code, update_invitation
)
from app.services_invitation import create_invitation_service

router = APIRouter()


# 响应模型定义
class InvitationData(BaseModel):
    id: str
    inviter_id: str
    invitee_id: str
    status: str
    reward_points: int
    reward_claimed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class InvitationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[InvitationData] = None


class InvitationsListData(BaseModel):
    invitations: list[InvitationData]
    total_count: int
    is_more: bool
    page: int
    page_size: int


class InvitationsListResponse(BaseModel):
    success: bool
    data: InvitationsListData


class InvitationStatsData(BaseModel):
    total_invitations: int
    completed_invitations: int
    pending_invitations: int
    total_reward_points: int
    claimed_reward_points: int


class InvitationStatsResponse(BaseModel):
    success: bool
    data: InvitationStatsData


class InviteCodeData(BaseModel):
    invite_code: str
    invite_url: str


class InviteCodeResponse(BaseModel):
    success: bool
    data: InviteCodeData


class InviteRegisterData(BaseModel):
    phone: str = Field(max_length=20, description="手机号")
    verification_code: str = Field(max_length=10, description="验证码")
    full_name: Optional[str] = None
    invite_code: str


class InviteRegisterResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


@router.get("/my-invite-code", response_model=InviteCodeResponse)
def get_my_invite_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> InviteCodeResponse:
    """
    获取当前用户的邀请码
    """
    return InviteCodeResponse(
        success=True,
        data=InviteCodeData(
            invite_code=current_user.invite_code,
            invite_url=f"http://31.40.205.69:8889/download?code={current_user.invite_code}"
        )
    )


@router.get("/my-invitations", response_model=InvitationsListData)
def get_my_invitations(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> InvitationsListData:
    """
    获取当前用户的邀请记录
    """
    skip = (page - 1) * page_size
    invitations, total = get_invitations_by_inviter(
        session=db, 
        inviter_id=current_user.id, 
        skip=skip, 
        limit=page_size
    )
    
    # 格式化邀请记录
    formatted_invitations = []
    for invitation in invitations:
        formatted_invitations.append(InvitationData(
            id=str(invitation.id),
            inviter_id=str(invitation.inviter_id),
            invitee_id=str(invitation.invitee_id),
            status=invitation.status.value,
            reward_points=invitation.reward_points,
            reward_claimed_at=invitation.reward_claimed_at,
            created_at=invitation.created_at,
            updated_at=invitation.updated_at
        ))
    
    return InvitationsListData(
            invitations=formatted_invitations,
            total_count=int(total),
            is_more=(page * page_size) < int(total),
            page=page,
            page_size=page_size
        )


@router.get("/stats", response_model=InvitationStatsResponse)
def get_invitation_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> InvitationStatsResponse:
    """
    获取当前用户的邀请统计
    """
    from app.crud_invitation import get_invitation_stats as crud_get_invitation_stats
    stats = crud_get_invitation_stats(session=db, user_id=current_user.id)
    
    return InvitationStatsResponse(
        success=True,
        data=InvitationStatsData(
            total_invitations=stats.total_invitations,
            completed_invitations=stats.completed_invitations,
            pending_invitations=stats.pending_invitations,
            total_reward_points=stats.total_reward_points,
            claimed_reward_points=stats.claimed_reward_points
        )
    )


@router.post("/register-with-invite", response_model=InviteRegisterResponse)
def register_with_invite(
    register_data: InviteRegisterData,
    db: Session = Depends(get_db)
) -> InviteRegisterResponse:
    """
    使用邀请码注册新用户（手机号注册）
    """
    invitation_service = create_invitation_service(db)
    result = invitation_service.register_with_invite_by_phone(
        phone=register_data.phone,
        verification_code=register_data.verification_code,
        full_name=register_data.full_name,
        invite_code=register_data.invite_code
    )
    
    return InviteRegisterResponse(
        success=result["success"],
        message=result["message"],
        data=result["data"]
    )


@router.post("/claim-reward/{invitation_id}", response_model=InvitationResponse)
def claim_invitation_reward(
    invitation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> InvitationResponse:
    """
    领取邀请奖励
    """
    invitation_service = create_invitation_service(db)
    result = invitation_service.claim_invitation_reward(
        invitation_id=uuid.UUID(invitation_id),
        user_id=current_user.id
    )
    
    if result.success:
        return InvitationResponse(
            success=True,
            message=result.message,
            data=InvitationData(
                id=str(result.data.id),
                inviter_id=str(result.data.inviter_id),
                invitee_id=str(result.data.invitee_id),
                status=result.data.status.value,
                reward_points=result.data.reward_points,
                reward_claimed_at=result.data.reward_claimed_at,
                created_at=result.data.created_at,
                updated_at=result.data.updated_at
            )
        )
    else:
        raise HTTPException(status_code=400, detail=result.message)


@router.get("/validate-invite-code/{invite_code}")
def validate_invite_code(
    invite_code: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    验证邀请码是否有效
    """
    user = get_user_by_invite_code(session=db, invite_code=invite_code)
    
    if user:
        return {
            "valid": True,
            "inviter_name": user.full_name or "匿名用户",
            "message": "邀请码有效"
        }
    else:
        return {
            "valid": False,
            "message": "邀请码无效或不存在"
        }
