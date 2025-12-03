"""
积分系统API路由
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import User, PointsHistoryQuery, MonthlyCheckInStats
from pydantic import BaseModel
from app.services_points import create_points_service
# 工具函数内联定义

router = APIRouter()


# 响应模型定义
class CheckInData(BaseModel):
    points_earned: int
    consecutive_days: int
    total_points: int
    current_rank: Optional[int]
    rank_display: str
    points_display: str


class CheckInResponse(BaseModel):
    success: bool
    message: str
    data: CheckInData


class TaskCompleteData(BaseModel):
    points_earned: int
    total_points: int
    current_rank: Optional[int]
    task_completion_count: int
    rank_display: str
    points_display: str


class TaskCompleteResponse(BaseModel):
    success: bool
    message: str
    data: TaskCompleteData


class LeaderboardEntry(BaseModel):
    user_id: str
    full_name: Optional[str]
    email: str
    points_balance: int
    points_display: str
    rank: int
    rank_display: str
    consecutive_check_in_days: int


class LeaderboardData(BaseModel):
    leaderboard: list[LeaderboardEntry]
    total_count: int
    user_rank: Optional[int]
    user_rank_display: str


class LeaderboardResponse(BaseModel):
    success: bool
    data: LeaderboardData


class UserStatsData(BaseModel):
    total_points: int
    points_display: str
    current_rank: Optional[int]
    rank_display: str
    consecutive_check_in_days: int
    total_check_ins: int
    total_tasks_completed: int
    points_this_month: int
    points_this_week: int
    points_today: int
    achievement: dict


class UserStatsResponse(BaseModel):
    success: bool
    data: UserStatsData


class PointsTransactionData(BaseModel):
    id: str
    points_change: int
    points_change_display: str
    balance_after: int
    balance_after_display: str
    source_type: str
    source_id: Optional[str]
    description: str
    created_at: datetime


class PointsHistoryData(BaseModel):
    transactions: list[PointsTransactionData]
    total_count: int
    is_more: bool
    page: int
    page_size: int


class PointsHistoryResponse(BaseModel):
    success: bool
    data: PointsHistoryData


class CheckInHistoryEntry(BaseModel):
    id: str
    check_in_date: datetime
    consecutive_days: int
    points_earned: int
    points_earned_display: str
    created_at: datetime


class CheckInHistoryData(BaseModel):
    check_ins: list[CheckInHistoryEntry]
    total_count: int
    is_more: bool
    page: int
    page_size: int


class CheckInHistoryResponse(BaseModel):
    success: bool
    data: CheckInHistoryData


class MonthlyCheckInData(BaseModel):
    year: int
    month: int
    total_days: int
    check_in_days: int
    consecutive_days: int
    points_earned: int
    points_earned_display: str
    check_in_dates: list[datetime]
    check_in_rate: float


class MonthlyCheckInResponse(BaseModel):
    success: bool
    data: MonthlyCheckInData


class UserTaskData(BaseModel):
    user_tasks: list
    total_count: int
    is_more: bool
    page: int
    page_size: int


class UserTaskResponse(BaseModel):
    success: bool
    data: UserTaskData


class TaskWithProgress(BaseModel):
    task_code: str
    title: str
    description: str
    points_reward: int
    task_type: str
    is_active: bool
    max_completions: Optional[int] = None
    cooldown_hours: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    conditions: Optional[str] = None
    button_text: Optional[str] = None
    uri: Optional[str] = None
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    # 进度信息
    current_completion_count: int = 0
    remaining_completions: Optional[int] = None
    can_complete: bool = True
    cooldown_remaining_hours: Optional[int] = None
    status: str = "in_progress"  # in_progress, completed, expired


class AvailableTaskResponse(BaseModel):
    tasks: list[TaskWithProgress]


class TaskProgressResponse(BaseModel):
    success: bool
    data: TaskWithProgress


class AchievementData(BaseModel):
    current_level: dict
    next_level: Optional[dict]
    points_to_next: int
    progress_percentage: float
    total_points: int
    points_display: str


class AchievementResponse(BaseModel):
    success: bool
    data: AchievementData


class CheckInDayData(BaseModel):
    day: int
    points: int
    state: str  # CHECKED_IN, TODAY_NOT_CHECKED_IN, FUTURE_NOT_CHECKED_IN, MISSED
    subtitle: Optional[str] = None
    is_special: bool = False


class CheckInCycleResponse(BaseModel):
    success: bool
    data: list[CheckInDayData]


# 工具函数
def format_points_display(points: int) -> str:
    """格式化积分显示"""
    if points >= 10000:
        return f"{points / 10000:.1f}万"
    elif points >= 1000:
        return f"{points / 1000:.1f}千"
    else:
        return str(points)


def get_rank_display(rank: Optional[int]) -> str:
    """获取排名显示文本"""
    if rank is None:
        return "未上榜"
    
    if rank == 1:
        return "第1名 🥇"
    elif rank == 2:
        return "第2名 🥈"
    elif rank == 3:
        return "第3名 🥉"
    elif rank <= 10:
        return f"第{rank}名"
    elif rank <= 100:
        return f"前100名"
    else:
        return f"第{rank}名"


def get_points_achievement_level(points: int) -> dict:
    """获取积分成就等级"""
    levels = [
        {"min_points": 0, "max_points": 99, "name": "新手", "icon": "🌱", "color": "#8B4513"},
        {"min_points": 100, "max_points": 499, "name": "青铜", "icon": "🥉", "color": "#CD7F32"},
        {"min_points": 500, "max_points": 999, "name": "白银", "icon": "🥈", "color": "#C0C0C0"},
        {"min_points": 1000, "max_points": 4999, "name": "黄金", "icon": "🥇", "color": "#FFD700"},
        {"min_points": 5000, "max_points": 9999, "name": "铂金", "icon": "💎", "color": "#E5E4E2"},
        {"min_points": 10000, "max_points": 49999, "name": "钻石", "icon": "💠", "color": "#B9F2FF"},
        {"min_points": 50000, "max_points": 99999, "name": "大师", "icon": "👑", "color": "#FF6B6B"},
        {"min_points": 100000, "max_points": float('inf'), "name": "传奇", "icon": "🌟", "color": "#FFD700"}
    ]
    
    for level in levels:
        if level["min_points"] <= points <= level["max_points"]:
            next_level = None
            for next_lvl in levels:
                if next_lvl["min_points"] > points:
                    next_level = next_lvl
                    break
            
            return {
                "current_level": level,
                "next_level": next_level,
                "points_to_next": next_level["min_points"] - points if next_level else 0,
                "progress_percentage": min(100, ((points - level["min_points"]) / (level["max_points"] - level["min_points"] + 1)) * 100)
            }
    
    return {
        "current_level": levels[0],
        "next_level": levels[1],
        "points_to_next": 100,
        "progress_percentage": 0
    }


@router.post("/check-in", response_model=CheckInResponse)
def check_in(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CheckInResponse:
    """
    用户签到
    """
    points_service = create_points_service(db)
    result = points_service.check_in(current_user.id)
    
    return CheckInResponse(
        success=result.success,
        message=result.message,
        data=CheckInData(
            points_earned=result.points_earned,
            consecutive_days=result.consecutive_days,
            total_points=result.total_points,
            current_rank=result.current_rank,
            rank_display=get_rank_display(result.current_rank),
            points_display=format_points_display(result.total_points)
        )
    )


@router.post("/tasks/{task_code}/complete", response_model=TaskCompleteResponse)
def complete_task(
    task_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TaskCompleteResponse:
    """
    完成任务
    """
    points_service = create_points_service(db)
    result = points_service.complete_task(current_user.id, task_code)
    
    return TaskCompleteResponse(
        success=result.success,
        message=result.message,
        data=TaskCompleteData(
            points_earned=result.points_earned,
            total_points=result.total_points,
            current_rank=result.current_rank,
            task_completion_count=result.task_completion_count,
            rank_display=get_rank_display(result.current_rank),
            points_display=format_points_display(result.total_points)
        )
    )


@router.get("/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(
    limit: int = Query(default=100, ge=1, le=1000, description="排行榜数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> LeaderboardResponse:
    """
    获取积分排行榜
    """
    points_service = create_points_service(db)
    result = points_service.get_leaderboard(limit=limit, user_id=current_user.id)
    
    # 格式化排行榜数据
    formatted_leaderboard = []
    for entry in result.data:
        formatted_leaderboard.append({
            "user_id": str(entry.user_id),
            "full_name": entry.full_name or "匿名用户",
            "email": entry.email,
            "points_balance": entry.points_balance,
            "points_display": format_points_display(entry.points_balance),
            "rank": entry.rank,
            "rank_display": get_rank_display(entry.rank),
            "consecutive_check_in_days": entry.consecutive_check_in_days
        })
    
    return LeaderboardResponse(
        success=True,
        data=LeaderboardData(
            leaderboard=formatted_leaderboard,
            total_count=result.count,
            user_rank=result.user_rank,
            user_rank_display=get_rank_display(result.user_rank)
        )
    )


@router.get("/stats", response_model=UserStatsResponse)
def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserStatsResponse:
    """
    获取用户积分统计
    """
    points_service = create_points_service(db)
    stats = points_service.get_user_stats(current_user.id)
    
    # 获取成就等级信息
    achievement = get_points_achievement_level(stats.total_points)
    
    return UserStatsResponse(
        success=True,
        data=UserStatsData(
            total_points=stats.total_points,
            points_display=format_points_display(stats.total_points),
            current_rank=stats.current_rank,
            rank_display=get_rank_display(stats.current_rank),
            consecutive_check_in_days=stats.consecutive_check_in_days,
            total_check_ins=stats.total_check_ins,
            total_tasks_completed=stats.total_tasks_completed,
            points_this_month=stats.points_this_month,
            points_this_week=stats.points_this_week,
            points_today=stats.points_today,
            achievement=achievement
        )
    )


@router.get("/history", response_model=PointsHistoryResponse)
def get_points_history(
    start_date: Optional[datetime] = Query(default=None, description="开始日期"),
    end_date: Optional[datetime] = Query(default=None, description="结束日期"),
    source_type: Optional[str] = Query(default=None, description="来源类型"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PointsHistoryResponse:
    """
    获取积分历史记录
    """
    points_service = create_points_service(db)
    
    query = PointsHistoryQuery(
        start_date=start_date,
        end_date=end_date,
        source_type=source_type,
        page=page,
        page_size=page_size
    )
    
    transactions, total, is_more = points_service.get_points_history(current_user.id, query)
    
    # 格式化交易记录
    formatted_transactions = []
    for transaction in transactions:
        formatted_transactions.append({
            "id": str(transaction.id),
            "points_change": transaction.points_change,
            "points_change_display": f"{'+' if transaction.points_change > 0 else ''}{transaction.points_change}",
            "balance_after": transaction.balance_after,
            "balance_after_display": format_points_display(transaction.balance_after),
            "source_type": transaction.source_type,
            "source_id": transaction.source_id,
            "description": transaction.description,
            "created_at": transaction.created_at
        })
    
    return PointsHistoryResponse(
        success=True,
        data=PointsHistoryData(
            transactions=formatted_transactions,
            total_count=total,
            is_more=is_more,
            page=page,
            page_size=page_size
        )
    )


@router.get("/check-in/history", response_model=CheckInHistoryResponse)
def get_check_in_history(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PointsHistoryResponse:
    """
    获取签到历史记录
    """
    points_service = create_points_service(db)
    skip = (page - 1) * page_size
    check_ins, total = points_service.get_check_in_history(current_user.id, skip, page_size)
    
    # 格式化签到记录
    formatted_check_ins = []
    for check_in in check_ins:
        formatted_check_ins.append({
            "id": str(check_in.id),
            "check_in_date": check_in.check_in_date,
            "consecutive_days": check_in.consecutive_days,
            "points_earned": check_in.points_earned,
            "points_earned_display": f"+{check_in.points_earned}",
            "created_at": check_in.created_at
        })
    
    return CheckInHistoryResponse(
        success=True,
        data=CheckInHistoryData(
            check_ins=formatted_check_ins,
            total_count=total,
            is_more=(page * page_size) < total,
            page=page,
            page_size=page_size
        )
    )


@router.get("/check-in/monthly/{year}/{month}", response_model=MonthlyCheckInResponse)
def get_monthly_check_in_stats(
    year: int,
    month: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PointsHistoryResponse:
    """
    获取月度签到统计
    """
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="月份必须在1-12之间")
    
    points_service = create_points_service(db)
    stats = points_service.get_monthly_check_in_stats(current_user.id, year, month)
    
    return MonthlyCheckInResponse(
        success=True,
        data=MonthlyCheckInData(
            year=stats.year,
            month=stats.month,
            total_days=stats.total_days,
            check_in_days=stats.check_in_days,
            consecutive_days=stats.consecutive_days,
            points_earned=stats.points_earned,
            points_earned_display=format_points_display(stats.points_earned),
            check_in_dates=stats.check_in_dates,
            check_in_rate=round((stats.check_in_days / stats.total_days) * 100, 2) if stats.total_days > 0 else 0
        )
    )


@router.get("/tasks", response_model=UserTaskResponse)
def get_user_tasks(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> PointsHistoryResponse:
    """
    获取用户任务列表
    """
    points_service = create_points_service(db)
    skip = (page - 1) * page_size
    user_tasks, total = points_service.get_user_tasks(current_user.id, skip, page_size)
    
    return UserTaskResponse(
        success=True,
        data=UserTaskData(
            user_tasks=user_tasks,
            total_count=total,
            is_more=(page * page_size) < total,
            page=page,
            page_size=page_size
        )
    )


@router.get("/tasks/available", response_model=AvailableTaskResponse)
def get_available_tasks(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AvailableTaskResponse:
    """
    获取可用任务列表（包含进度信息）
    """
    points_service = create_points_service(db)
    skip = (page - 1) * page_size
    tasks = points_service.get_available_tasks_with_progress(current_user.id, skip, page_size)
    
    return AvailableTaskResponse(tasks=tasks)


@router.get("/tasks/{task_code}/progress", response_model=TaskProgressResponse)
def get_task_progress(
    task_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TaskProgressResponse:
    """
    获取特定任务的完成进度
    """
    points_service = create_points_service(db)
    
    # 获取任务信息
    from app.crud_points import get_task_by_code
    task = get_task_by_code(session=db, task_code=task_code)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取带进度信息的任务数据
    tasks = points_service.get_available_tasks_with_progress(current_user.id, skip=0, limit=1)
    
    # 查找指定任务
    task_with_progress = None
    for t in tasks:
        if t["task_code"] == task_code:
            task_with_progress = t
            break
    
    if not task_with_progress:
        raise HTTPException(status_code=404, detail="任务不存在或不可用")
    
    return TaskProgressResponse(
        success=True,
        data=TaskWithProgress(**task_with_progress)
    )


@router.get("/achievement", response_model=AchievementResponse)
def get_achievement_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AchievementResponse:
    """
    获取用户成就等级信息
    """
    points_service = create_points_service(db)
    stats = points_service.get_user_stats(current_user.id)
    achievement = get_points_achievement_level(stats.total_points)
    
    return AchievementResponse(
        success=True,
        data=AchievementData(
            current_level=achievement["current_level"],
            next_level=achievement["next_level"],
            points_to_next=achievement["points_to_next"],
            progress_percentage=achievement["progress_percentage"],
            total_points=stats.total_points,
            points_display=format_points_display(stats.total_points)
        )
    )


@router.get("/check-in/cycle", response_model=CheckInCycleResponse)
def get_check_in_cycle(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CheckInCycleResponse:
    """
    获取用户7天签到周期的当前状态
    """
    points_service = create_points_service(db)
    
    # 获取当前时间
    now = datetime.now()
    today = now.date()
    
    # 获取用户最近7天的签到历史
    check_ins, _ = points_service.get_check_in_history(
        current_user.id, 
        skip=0, 
        limit=7
    )
    
    # 创建签到日期映射，用于快速查找
    check_in_map = {}
    for check_in in check_ins:
        check_in_date = check_in.check_in_date.date()
        check_in_map[check_in_date] = check_in
    
    # 找到最近一次签到的日期
    last_check_in_date = None
    if check_ins:
        last_check_in_date = max(check_in.check_in_date.date() for check_in in check_ins)
    
    # 计算连续签到天数（从最近签到日期开始往前计算）
    consecutive_days = 0
    first_consecutive_date = None
    if last_check_in_date:
        current_date = last_check_in_date
        # 从最近签到日期开始往前查找连续签到
        while current_date in check_in_map:
            consecutive_days += 1
            first_consecutive_date = current_date  # 记录连续签到的第一天
            current_date = current_date - timedelta(days=1)
    
    # 确定签到周期的起始日期
    # 从连续签到的第一天开始，如果没有连续签到则从今天开始
    if first_consecutive_date:
        cycle_start_date = first_consecutive_date
    else:
        cycle_start_date = today
    
    # 生成7天签到周期数据（从周期起始日期开始）
    cycle_data = []
    
    for day in range(1, 8):
        target_date = cycle_start_date + timedelta(days=day-1)
        points = 10 + (day - 1)  # 第1天10分，第2天11分...
        
        # 判断状态
        if target_date in check_in_map:
            state = "CHECKED_IN"
        elif target_date == today:
            state = "TODAY_NOT_CHECKED_IN"
        elif target_date < today:
            state = "MISSED"
        else:
            state = "FUTURE_NOT_CHECKED_IN"
        
        # 第7天特殊处理
        if day == 7:
            cycle_data.append(CheckInDayData(
                day=day,
                points=0,
                state=state,
                subtitle="惊喜大礼包",
                is_special=True
            ))
        else:
            cycle_data.append(CheckInDayData(
                day=day,
                points=points,
                state=state,
                is_special=False
            ))
    
    return CheckInCycleResponse(
        success=True,
        data=cycle_data
    )
