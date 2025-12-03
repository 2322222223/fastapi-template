"""
抽奖系统API路由
"""
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import (
    User, LotteryActivity, LotteryPrize, LotteryRecord, UserPrize,
    LotteryActivityCreate, LotteryActivityUpdate, LotteryActivityPublic,
    LotteryPrizeCreate, LotteryPrizeUpdate, LotteryPrizePublic,
    LotteryRecordPublic, UserPrizePublic, UserPrizeUpdate,
    LotteryDrawRequest, LotteryDrawResponse,
    LotteryActivitiesResponse, LotteryPrizesResponse,
    UserLotteryRecordsResponse, UserPrizesResponse,
    LotteryActivityStatus, PrizeType, UserPrizeStatus
)
from app.crud_lottery import (
    create_lottery_activity, get_lottery_activity, get_lottery_activities,
    update_lottery_activity, delete_lottery_activity,
    create_lottery_prize, get_lottery_prize, get_lottery_prizes_by_activity,
    update_lottery_prize, delete_lottery_prize,
    get_user_lottery_records, get_user_prizes, update_user_prize,
    process_prize_draw, get_activity_statistics, get_user_draw_count
)
from app.crud_points import get_user_points_balance

router = APIRouter()


# ==================== 抽奖活动管理 ====================

@router.post("/activities", response_model=LotteryActivityPublic)
def create_activity(
    activity: LotteryActivityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建抽奖活动（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    db_activity = create_lottery_activity(session=db, lottery_activity=activity)
    return LotteryActivityPublic.model_validate(db_activity)


@router.get("/activities/{activity_id}", response_model=LotteryActivityPublic)
def get_activity(
    activity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取抽奖活动详情"""
    activity = get_lottery_activity(session=db, activity_id=activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    
    # 获取统计信息
    stats = get_activity_statistics(session=db, activity_id=activity_id)
    activity_public = LotteryActivityPublic.model_validate(activity)
    activity_public.prize_count = stats.get("prize_count", 0)
    activity_public.total_draws = stats.get("total_draws", 0)
    
    return activity_public


@router.get("/activities", response_model=LotteryActivitiesResponse)
def get_activities(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: Optional[LotteryActivityStatus] = Query(default=None, description="活动状态"),
    is_active: Optional[bool] = Query(default=None, description="是否启用"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取抽奖活动列表"""
    skip = (page - 1) * page_size
    activities, total = get_lottery_activities(
        session=db, skip=skip, limit=page_size,
        status=status, is_active=is_active
    )
    
    # 转换为公开模型并添加统计信息
    activity_list = []
    for activity in activities:
        stats = get_activity_statistics(session=db, activity_id=activity.id)
        activity_public = LotteryActivityPublic.model_validate(activity)
        activity_public.prize_count = stats.get("prize_count", 0)
        activity_public.total_draws = stats.get("total_draws", 0)
        activity_list.append(activity_public)
    
    return LotteryActivitiesResponse(
        success=True,
        message="获取活动列表成功",
        data=activity_list,
        total=total,
        page=page,
        page_size=page_size
    )


@router.put("/activities/{activity_id}", response_model=LotteryActivityPublic)
def update_activity(
    activity_id: uuid.UUID,
    activity_update: LotteryActivityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新抽奖活动（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    db_activity = update_lottery_activity(
        session=db, activity_id=activity_id, lottery_activity_update=activity_update
    )
    if not db_activity:
        raise HTTPException(status_code=404, detail="活动不存在")
    
    return LotteryActivityPublic.model_validate(db_activity)


@router.delete("/activities/{activity_id}")
def delete_activity(
    activity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除抽奖活动（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    success = delete_lottery_activity(session=db, activity_id=activity_id)
    if not success:
        raise HTTPException(status_code=404, detail="活动不存在")
    
    return {"success": True, "message": "活动删除成功"}


# ==================== 抽奖奖品管理 ====================

@router.post("/prizes", response_model=LotteryPrizePublic)
def create_prize(
    prize: LotteryPrizeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建抽奖奖品（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    db_prize = create_lottery_prize(session=db, lottery_prize=prize)
    return LotteryPrizePublic.model_validate(db_prize)


@router.get("/activities/{activity_id}/prizes", response_model=LotteryPrizesResponse)
def get_activity_prizes(
    activity_id: uuid.UUID,
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    is_active: Optional[bool] = Query(default=None, description="是否启用"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取活动的奖品列表"""
    skip = (page - 1) * page_size
    prizes, total = get_lottery_prizes_by_activity(
        session=db, activity_id=activity_id, skip=skip, limit=page_size,
        is_active=is_active
    )
    
    prize_list = [LotteryPrizePublic.model_validate(prize) for prize in prizes]
    
    return LotteryPrizesResponse(
        success=True,
        message="获取奖品列表成功",
        data=prize_list,
        total=total,
        page=page,
        page_size=page_size
    )


@router.put("/prizes/{prize_id}", response_model=LotteryPrizePublic)
def update_prize(
    prize_id: uuid.UUID,
    prize_update: LotteryPrizeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新抽奖奖品（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    db_prize = update_lottery_prize(
        session=db, prize_id=prize_id, lottery_prize_update=prize_update
    )
    if not db_prize:
        raise HTTPException(status_code=404, detail="奖品不存在")
    
    return LotteryPrizePublic.model_validate(db_prize)


@router.delete("/prizes/{prize_id}")
def delete_prize(
    prize_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除抽奖奖品（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    success = delete_lottery_prize(session=db, prize_id=prize_id)
    if not success:
        raise HTTPException(status_code=404, detail="奖品不存在")
    
    return {"success": True, "message": "奖品删除成功"}


# ==================== 用户抽奖接口 ====================

@router.post("/draw", response_model=LotteryDrawResponse)
def draw_prize(
    draw_request: LotteryDrawRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """用户抽奖"""
    prize, message = process_prize_draw(
        session=db, user_id=current_user.id, activity_id=draw_request.activity_id
    )
    
    if not prize:
        return LotteryDrawResponse(
            success=False,
            message=message,
            prize=None,
            points_balance=get_user_points_balance(session=db, user_id=current_user.id)
        )
    
    # 获取用户剩余抽奖次数
    activity = get_lottery_activity(session=db, activity_id=draw_request.activity_id)
    remaining_draws = None
    if activity and activity.max_draws_per_user:
        user_draw_count = get_user_draw_count(
            session=db, user_id=current_user.id, activity_id=draw_request.activity_id
        )
        remaining_draws = max(0, activity.max_draws_per_user - user_draw_count)
    
    return LotteryDrawResponse(
        success=True,
        message=message,
        prize=LotteryPrizePublic.model_validate(prize),
        points_balance=get_user_points_balance(session=db, user_id=current_user.id),
        remaining_draws=remaining_draws
    )


@router.get("/my-records", response_model=UserLotteryRecordsResponse)
def get_my_lottery_records(
    activity_id: Optional[uuid.UUID] = Query(default=None, description="活动ID"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的抽奖记录"""
    skip = (page - 1) * page_size
    records, total = get_user_lottery_records(
        session=db, user_id=current_user.id, activity_id=activity_id,
        skip=skip, limit=page_size
    )
    
    record_list = []
    for record in records:
        record_public = LotteryRecordPublic.model_validate(record)
        if record.prize:
            record_public.prize = LotteryPrizePublic.model_validate(record.prize)
        record_list.append(record_public)
    
    return UserLotteryRecordsResponse(
        success=True,
        message="获取抽奖记录成功",
        data=record_list,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/my-prizes", response_model=UserPrizesResponse)
def get_my_prizes(
    status: Optional[UserPrizeStatus] = Query(default=None, description="奖品状态"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的奖品"""
    skip = (page - 1) * page_size
    prizes, total = get_user_prizes(
        session=db, user_id=current_user.id, status=status,
        skip=skip, limit=page_size
    )
    
    prize_list = []
    for prize in prizes:
        prize_public = UserPrizePublic.model_validate(prize)
        if prize.prize:
            prize_public.prize = LotteryPrizePublic.model_validate(prize.prize)
        prize_list.append(prize_public)
    
    return UserPrizesResponse(
        success=True,
        message="获取奖品列表成功",
        data=prize_list,
        total=total,
        page=page,
        page_size=page_size
    )


@router.put("/my-prizes/{prize_id}/claim", response_model=UserPrizePublic)
def claim_prize(
    prize_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """领取奖品"""
    # 获取用户奖品
    user_prize = db.query(UserPrize).filter(
        UserPrize.id == prize_id,
        UserPrize.user_id == current_user.id
    ).first()
    
    if not user_prize:
        raise HTTPException(status_code=404, detail="奖品不存在")
    
    if user_prize.status != UserPrizeStatus.PENDING:
        raise HTTPException(status_code=400, detail="奖品状态不允许领取")
    
    # 更新奖品状态
    update_data = UserPrizeUpdate(
        status=UserPrizeStatus.CLAIMED,
        claimed_at=datetime.utcnow()
    )
    
    updated_prize = update_user_prize(
        session=db, user_prize_id=prize_id, user_prize_update=update_data
    )
    
    if not updated_prize:
        raise HTTPException(status_code=404, detail="奖品不存在")
    
    prize_public = UserPrizePublic.model_validate(updated_prize)
    if updated_prize.prize:
        prize_public.prize = LotteryPrizePublic.model_validate(updated_prize.prize)
    
    return prize_public


# ==================== 活动统计接口 ====================

@router.get("/activities/{activity_id}/stats")
def get_activity_stats(
    activity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取活动统计信息（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    stats = get_activity_statistics(session=db, activity_id=activity_id)
    if not stats:
        raise HTTPException(status_code=404, detail="活动不存在")
    
    return {
        "success": True,
        "message": "获取统计信息成功",
        "data": stats
    }
