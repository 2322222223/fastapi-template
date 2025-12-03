"""
积分系统CRUD操作
"""
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import and_, or_, desc, func, text
from sqlalchemy.orm import Session
from sqlmodel import select

from app.models import (
    User, PointsTransaction, CheckInHistory, Task, UserTask,
    PointsTransactionCreate, CheckInHistoryCreate, TaskCreate, UserTaskCreate,
    PointsTransactionPublic, CheckInHistoryPublic, TaskPublic, UserTaskPublic,
    PointsLeaderboardEntry, UserPointsStats, MonthlyCheckInStats,
    PointsSourceType, TaskType, UserTaskStatus
)


# ==================== 积分流水相关操作 ====================

def create_points_transaction(
    *, session: Session, points_transaction: PointsTransactionCreate
) -> PointsTransaction:
    """创建积分流水记录"""
    db_obj = PointsTransaction.model_validate(
        points_transaction, update={"id": uuid.uuid4()}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_points_transactions(
    *,
    session: Session,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    source_type: Optional[PointsSourceType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Tuple[List[PointsTransactionPublic], int]:
    """获取用户积分流水记录"""
    query = select(PointsTransaction).where(PointsTransaction.user_id == user_id)
    
    if source_type:
        query = query.where(PointsTransaction.source_type == source_type)
    
    if start_date:
        query = query.where(PointsTransaction.created_at >= start_date)
    
    if end_date:
        query = query.where(PointsTransaction.created_at <= end_date)
    
    # 获取总数
    count_query = select(func.count(PointsTransaction.id)).where(PointsTransaction.user_id == user_id)
    if source_type:
        count_query = count_query.where(PointsTransaction.source_type == source_type)
    if start_date:
        count_query = count_query.where(PointsTransaction.created_at >= start_date)
    if end_date:
        count_query = count_query.where(PointsTransaction.created_at <= end_date)
    
    total = session.exec(count_query).one()
    
    # 获取分页数据
    query = query.order_by(desc(PointsTransaction.created_at)).offset(skip).limit(limit)
    results = session.exec(query).all()
    
    return [PointsTransactionPublic.model_validate(result) for result in results], total


def get_user_points_balance(*, session: Session, user_id: uuid.UUID) -> int:
    """获取用户当前积分余额"""
    user = session.get(User, user_id)
    return user.points_balance if user else 0


def update_user_points_balance(
    *, session: Session, user_id: uuid.UUID, new_balance: int
) -> bool:
    """更新用户积分余额"""
    user = session.get(User, user_id)
    if not user:
        return False
    
    user.points_balance = new_balance
    session.commit()
    return True


# ==================== 签到相关操作 ====================

def create_check_in_history(
    *, session: Session, check_in_history: CheckInHistoryCreate
) -> CheckInHistory:
    """创建签到记录"""
    db_obj = CheckInHistory.model_validate(
        check_in_history, update={"id": uuid.uuid4()}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_user_check_in_today(
    *, session: Session, user_id: uuid.UUID
) -> Optional[CheckInHistory]:
    """获取用户今日签到记录"""
    today = datetime.now().date()
    query = select(CheckInHistory).where(
        and_(
            CheckInHistory.user_id == user_id,
            func.date(CheckInHistory.check_in_date) == today
        )
    )
    return session.exec(query).first()


def get_user_last_check_in(
    *, session: Session, user_id: uuid.UUID
) -> Optional[CheckInHistory]:
    """获取用户最后一次签到记录"""
    query = select(CheckInHistory).where(
        CheckInHistory.user_id == user_id
    ).order_by(desc(CheckInHistory.check_in_date)).limit(1)
    return session.exec(query).first()


def get_user_check_in_history(
    *, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> Tuple[List[CheckInHistoryPublic], int]:
    """获取用户签到历史"""
    query = select(CheckInHistory).where(CheckInHistory.user_id == user_id)
    
    # 获取总数
    count_query = select(func.count(CheckInHistory.id)).where(CheckInHistory.user_id == user_id)
    total = session.exec(count_query).one()
    
    # 获取分页数据
    query = query.order_by(desc(CheckInHistory.check_in_date)).offset(skip).limit(limit)
    results = session.exec(query).all()
    
    return [CheckInHistoryPublic.model_validate(result) for result in results], total


def get_user_consecutive_check_in_days(
    *, session: Session, user_id: uuid.UUID
) -> int:
    """获取用户连续签到天数"""
    last_check_in = get_user_last_check_in(session=session, user_id=user_id)
    if not last_check_in:
        return 0
    
    return last_check_in.consecutive_days


def get_monthly_check_in_stats(
    *, session: Session, user_id: uuid.UUID, year: int, month: int
) -> MonthlyCheckInStats:
    """获取用户月度签到统计"""
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # 获取该月所有签到记录
    query = select(CheckInHistory).where(
        and_(
            CheckInHistory.user_id == user_id,
            CheckInHistory.check_in_date >= start_date,
            CheckInHistory.check_in_date < end_date
        )
    ).order_by(CheckInHistory.check_in_date)
    
    check_ins = session.exec(query).all()
    
    # 计算统计数据
    total_days = (end_date - start_date).days
    check_in_days = len(check_ins)
    points_earned = sum(check_in.points_earned for check_in in check_ins)
    consecutive_days = check_ins[-1].consecutive_days if check_ins else 0
    check_in_dates = [check_in.check_in_date for check_in in check_ins]
    
    return MonthlyCheckInStats(
        year=year,
        month=month,
        total_days=total_days,
        check_in_days=check_in_days,
        consecutive_days=consecutive_days,
        points_earned=points_earned,
        check_in_dates=check_in_dates
    )


# ==================== 任务相关操作 ====================

def create_task(*, session: Session, task: TaskCreate) -> Task:
    """创建任务"""
    db_obj = Task.model_validate(task, update={"id": uuid.uuid4()})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_task(*, session: Session, task_id: uuid.UUID) -> Optional[Task]:
    """获取任务详情"""
    return session.get(Task, task_id)


def get_task_by_code(*, session: Session, task_code: str) -> Optional[Task]:
    """根据任务代码获取任务"""
    query = select(Task).where(Task.task_code == task_code)
    return session.exec(query).first()


def get_active_tasks(
    *, session: Session, skip: int = 0, limit: int = 100
) -> Tuple[List[TaskPublic], int]:
    """获取活跃任务列表"""
    query = select(Task).where(Task.is_active == True)
    
    # 获取总数
    count_query = select(func.count(Task.id)).where(Task.is_active == True)
    total = session.exec(count_query).one()
    
    # 获取分页数据
    query = query.order_by(desc(Task.created_at)).offset(skip).limit(limit)
    results = session.exec(query).all()
    
    return [TaskPublic.model_validate(result) for result in results], total


def update_task(*, session: Session, task_id: uuid.UUID, task_update: dict) -> Optional[Task]:
    """更新任务"""
    task = session.get(Task, task_id)
    if not task:
        return None
    
    for field, value in task_update.items():
        if hasattr(task, field) and value is not None:
            setattr(task, field, value)
    
    task.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(task)
    return task


# ==================== 用户任务相关操作 ====================

def create_user_task(*, session: Session, user_task: UserTaskCreate) -> UserTask:
    """创建用户任务记录"""
    db_obj = UserTask.model_validate(user_task, update={"id": uuid.uuid4()})
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_user_task(
    *, session: Session, user_id: uuid.UUID, task_id: uuid.UUID
) -> Optional[UserTask]:
    """获取用户任务记录"""
    query = select(UserTask).where(
        and_(UserTask.user_id == user_id, UserTask.task_id == task_id)
    )
    return session.exec(query).first()


def get_user_tasks(
    *, session: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> Tuple[List[UserTaskPublic], int]:
    """获取用户任务列表"""
    query = select(UserTask).where(UserTask.user_id == user_id)
    
    # 获取总数
    count_query = select(func.count(UserTask.id)).where(UserTask.user_id == user_id)
    total = session.exec(count_query).one()
    
    # 获取分页数据
    query = query.order_by(desc(UserTask.created_at)).offset(skip).limit(limit)
    results = session.exec(query).all()
    
    return [UserTaskPublic.model_validate(result) for result in results], total


def update_user_task(
    *, session: Session, user_task_id: uuid.UUID, user_task_update: dict
) -> Optional[UserTask]:
    """更新用户任务"""
    user_task = session.get(UserTask, user_task_id)
    if not user_task:
        return None
    
    for field, value in user_task_update.items():
        if hasattr(user_task, field) and value is not None:
            setattr(user_task, field, value)
    
    user_task.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(user_task)
    return user_task


def get_user_completed_tasks_count(
    *, session: Session, user_id: uuid.UUID
) -> int:
    """获取用户已完成任务数量"""
    query = select(func.count(UserTask.id)).where(
        and_(
            UserTask.user_id == user_id,
            UserTask.status == UserTaskStatus.COMPLETED
        )
    )
    return session.exec(query).one()


# ==================== 排行榜相关操作 ====================

def get_points_leaderboard(
    *, session: Session, limit: int = 100, user_id: Optional[uuid.UUID] = None
) -> Tuple[List[PointsLeaderboardEntry], int, Optional[int]]:
    """获取积分排行榜"""
    # 构建查询，包含用户信息和连续签到天数
    query = select(
        User.id,
        User.full_name,
        User.email,
        User.points_balance,
        func.coalesce(
            select(CheckInHistory.consecutive_days)
            .where(CheckInHistory.user_id == User.id)
            .order_by(desc(CheckInHistory.check_in_date))
            .limit(1),
            0
        ).label("consecutive_check_in_days")
    ).where(User.is_active == True).order_by(desc(User.points_balance))
    
    # 获取总数
    count_query = select(func.count(User.id)).where(User.is_active == True)
    total = session.exec(count_query).one()
    
    # 获取分页数据
    query = query.limit(limit)
    results = session.exec(query).all()
    
    # 构建排行榜条目
    leaderboard = []
    user_rank = None
    
    for rank, result in enumerate(results, 1):
        entry = PointsLeaderboardEntry(
            user_id=result.id,
            full_name=result.full_name,
            email=result.email,
            points_balance=result.points_balance,
            rank=rank,
            consecutive_check_in_days=result.consecutive_check_in_days
        )
        leaderboard.append(entry)
        
        # 记录当前用户排名
        if user_id and result.id == user_id:
            user_rank = rank
    
    return leaderboard, total, user_rank


def get_user_rank(*, session: Session, user_id: uuid.UUID) -> Optional[int]:
    """获取用户排名"""
    # 使用窗口函数计算排名
    query = text("""
        SELECT rank FROM (
            SELECT id, ROW_NUMBER() OVER (ORDER BY points_balance DESC) as rank
            FROM "user" 
            WHERE is_active = true
        ) ranked_users 
        WHERE id = :user_id
    """)
    
    result = session.execute(query, {"user_id": user_id}).first()
    return result[0] if result else None


# ==================== 积分统计相关操作 ====================

def get_user_points_stats(*, session: Session, user_id: uuid.UUID) -> UserPointsStats:
    """获取用户积分统计信息"""
    # 获取用户基本信息
    user = session.get(User, user_id)
    if not user:
        return UserPointsStats(
            total_points=0, current_rank=None, consecutive_check_in_days=0,
            total_check_ins=0, total_tasks_completed=0, points_this_month=0,
            points_this_week=0, points_today=0
        )
    
    # 获取当前排名
    current_rank = get_user_rank(session=session, user_id=user_id)
    
    # 获取连续签到天数
    consecutive_days = get_user_consecutive_check_in_days(session=session, user_id=user_id)
    
    # 获取总签到次数
    total_check_ins_query = select(func.count(CheckInHistory.id)).where(
        CheckInHistory.user_id == user_id
    )
    total_check_ins = session.exec(total_check_ins_query).one()
    
    # 获取已完成任务数量
    total_tasks_completed = get_user_completed_tasks_count(session=session, user_id=user_id)
    
    # 获取本月积分
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    points_this_month_query = select(func.sum(PointsTransaction.points_change)).where(
        and_(
            PointsTransaction.user_id == user_id,
            PointsTransaction.points_change > 0,
            PointsTransaction.created_at >= month_start
        )
    )
    points_this_month = session.exec(points_this_month_query).one() or 0
    
    # 获取本周积分
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    points_this_week_query = select(func.sum(PointsTransaction.points_change)).where(
        and_(
            PointsTransaction.user_id == user_id,
            PointsTransaction.points_change > 0,
            PointsTransaction.created_at >= week_start
        )
    )
    points_this_week = session.exec(points_this_week_query).one() or 0
    
    # 获取今日积分
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    points_today_query = select(func.sum(PointsTransaction.points_change)).where(
        and_(
            PointsTransaction.user_id == user_id,
            PointsTransaction.points_change > 0,
            PointsTransaction.created_at >= today_start
        )
    )
    points_today = session.exec(points_today_query).one() or 0
    
    return UserPointsStats(
        total_points=user.points_balance,
        current_rank=current_rank,
        consecutive_check_in_days=consecutive_days,
        total_check_ins=total_check_ins,
        total_tasks_completed=total_tasks_completed,
        points_this_month=points_this_month,
        points_this_week=points_this_week,
        points_today=points_today
    )
