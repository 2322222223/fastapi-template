"""
积分系统业务逻辑服务
"""
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import (
    User, PointsTransaction, CheckInHistory, Task, UserTask,
    PointsTransactionCreate, CheckInHistoryCreate, UserTaskCreate,
    CheckInResponse, TaskCompleteResponse, PointsLeaderboardPublic,
    UserPointsStats, MonthlyCheckInStats, PointsHistoryQuery,
    PointsSourceType, TaskType, UserTaskStatus
)
from app.crud_points import (
    create_points_transaction, get_user_points_balance, update_user_points_balance,
    create_check_in_history, get_user_check_in_today, get_user_last_check_in,
    get_user_consecutive_check_in_days, get_monthly_check_in_stats,
    get_task_by_code, get_user_task, create_user_task, update_user_task,
    get_points_leaderboard, get_user_points_stats, get_user_rank,
    get_points_transactions, get_user_check_in_history, get_user_tasks,
    get_active_tasks
)


class PointsService:
    """积分系统业务逻辑服务"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def check_in(self, user_id: uuid.UUID) -> CheckInResponse:
        """用户签到"""
        try:
            # 检查今日是否已签到
            today_check_in = get_user_check_in_today(session=self.session, user_id=user_id)
            if today_check_in:
                return CheckInResponse(
                    success=False,
                    message="今日已签到，请明天再来",
                    points_earned=0,
                    consecutive_days=0,
                    total_points=get_user_points_balance(session=self.session, user_id=user_id),
                    current_rank=None
                )
            
            # 获取用户最后一次签到记录
            last_check_in = get_user_last_check_in(session=self.session, user_id=user_id)
            
            # 计算连续签到天数
            consecutive_days = 1
            if last_check_in:
                last_check_in_date = last_check_in.check_in_date.date()
                yesterday = (datetime.now() - timedelta(days=1)).date()
                
                if last_check_in_date == yesterday:
                    # 连续签到
                    consecutive_days = last_check_in.consecutive_days + 1
                else:
                    # 连签中断
                    consecutive_days = 1
            
            # 计算本次签到积分：基础10分 + 连续天数-1
            points_earned = 10 + (consecutive_days - 1)
            
            # 更新用户积分余额
            current_balance = get_user_points_balance(session=self.session, user_id=user_id)
            new_balance = current_balance + points_earned
            update_user_points_balance(session=self.session, user_id=user_id, new_balance=new_balance)
            
            # 创建签到记录
            check_in_history = CheckInHistoryCreate(
                user_id=user_id,
                check_in_date=datetime.now(),
                consecutive_days=consecutive_days,
                points_earned=points_earned
            )
            create_check_in_history(session=self.session, check_in_history=check_in_history)
            
            # 创建积分流水记录
            points_transaction = PointsTransactionCreate(
                user_id=user_id,
                points_change=points_earned,
                balance_after=new_balance,
                source_type=PointsSourceType.CHECK_IN,
                source_id=datetime.now().strftime("%Y-%m-%d"),
                description=f"连续签到第{consecutive_days}天"
            )
            create_points_transaction(session=self.session, points_transaction=points_transaction)
            
            # 获取当前排名
            current_rank = get_user_rank(session=self.session, user_id=user_id)
            
            return CheckInResponse(
                success=True,
                message=f"签到成功！连续签到{consecutive_days}天",
                points_earned=points_earned,
                consecutive_days=consecutive_days,
                total_points=new_balance,
                current_rank=current_rank
            )
                
        except Exception as e:
            return CheckInResponse(
                success=False,
                message=f"签到失败：{str(e)}",
                points_earned=0,
                consecutive_days=0,
                total_points=get_user_points_balance(session=self.session, user_id=user_id),
                current_rank=None
            )
    
    def complete_task(self, user_id: uuid.UUID, task_code: str) -> TaskCompleteResponse:
        """完成任务"""
        try:
            # 获取任务信息
            task = get_task_by_code(session=self.session, task_code=task_code)
            if not task:
                return TaskCompleteResponse(
                    success=False,
                    message="任务不存在",
                    points_earned=0,
                    total_points=get_user_points_balance(session=self.session, user_id=user_id),
                    current_rank=None,
                    task_completion_count=0
                )
            
            if not task.is_active:
                return TaskCompleteResponse(
                    success=False,
                    message="任务已停用",
                    points_earned=0,
                    total_points=get_user_points_balance(session=self.session, user_id=user_id),
                    current_rank=None,
                    task_completion_count=0
                )
            
            # 检查任务是否在有效期内
            now = datetime.now()
            if task.start_date and now < task.start_date:
                return TaskCompleteResponse(
                    success=False,
                    message="任务尚未开始",
                    points_earned=0,
                    total_points=get_user_points_balance(session=self.session, user_id=user_id),
                    current_rank=None,
                    task_completion_count=0
                )
            
            if task.end_date and now > task.end_date:
                return TaskCompleteResponse(
                    success=False,
                    message="任务已过期",
                    points_earned=0,
                    total_points=get_user_points_balance(session=self.session, user_id=user_id),
                    current_rank=None,
                    task_completion_count=0
                )
            
            # 获取或创建用户任务记录
            user_task = get_user_task(session=self.session, user_id=user_id, task_id=task.id)
            if not user_task:
                user_task = create_user_task(session=self.session, user_task=UserTaskCreate(
                    user_id=user_id,
                    task_id=task.id,
                    status=UserTaskStatus.IN_PROGRESS
                ))
            
            # 检查任务是否已完成（只对一次性任务检查）
            if task.task_type == TaskType.ONE_TIME and user_task.status == UserTaskStatus.COMPLETED:
                return TaskCompleteResponse(
                    success=False,
                    message="任务已完成",
                    points_earned=0,
                    total_points=get_user_points_balance(session=self.session, user_id=user_id),
                    current_rank=None,
                    task_completion_count=user_task.completion_count
                )
            
            # 检查冷却时间
            if task.cooldown_hours and user_task.last_completed_at:
                cooldown_end = user_task.last_completed_at + timedelta(hours=task.cooldown_hours)
                if now < cooldown_end:
                    remaining_time = cooldown_end - now
                    return TaskCompleteResponse(
                        success=False,
                        message=f"任务冷却中，请{remaining_time.seconds // 3600}小时后再试",
                        points_earned=0,
                        total_points=get_user_points_balance(session=self.session, user_id=user_id),
                        current_rank=None,
                        task_completion_count=user_task.completion_count
                    )
            
            # 检查最大完成次数
            if task.max_completions and user_task.completion_count >= task.max_completions:
                return TaskCompleteResponse(
                    success=False,
                    message="任务已完成最大次数",
                    points_earned=0,
                    total_points=get_user_points_balance(session=self.session, user_id=user_id),
                    current_rank=None,
                    task_completion_count=user_task.completion_count
                )
            
            # 更新用户积分余额
            current_balance = get_user_points_balance(session=self.session, user_id=user_id)
            new_balance = current_balance + task.points_reward
            update_user_points_balance(session=self.session, user_id=user_id, new_balance=new_balance)
            
            # 更新用户任务状态
            new_completion_count = user_task.completion_count + 1
            
            # 根据任务类型和完成次数决定新状态
            if task.task_type == TaskType.ONE_TIME:
                # 一次性任务：完成后状态改为已完成
                new_status = UserTaskStatus.COMPLETED
            elif task.task_type == TaskType.REPEATABLE:
                # 重复任务：检查是否达到最大完成次数
                if task.max_completions and new_completion_count >= task.max_completions:
                    new_status = UserTaskStatus.COMPLETED
                else:
                    new_status = UserTaskStatus.IN_PROGRESS
            else:  # DAILY
                # 每日任务：保持进行中状态
                new_status = UserTaskStatus.IN_PROGRESS
            
            update_user_task(session=self.session, user_task_id=user_task.id, user_task_update={
                "status": new_status,
                "completed_at": now,
                "completion_count": new_completion_count,
                "last_completed_at": now
            })
            
            # 创建积分流水记录
            points_transaction = PointsTransactionCreate(
                user_id=user_id,
                points_change=task.points_reward,
                balance_after=new_balance,
                source_type=PointsSourceType.TASK_COMPLETE,
                source_id=str(task.id),
                description=f"完成任务：{task.title}"
            )
            create_points_transaction(session=self.session, points_transaction=points_transaction)
            
            # 获取当前排名
            current_rank = get_user_rank(session=self.session, user_id=user_id)
            
            return TaskCompleteResponse(
                success=True,
                message=f"任务完成！获得{task.points_reward}积分",
                points_earned=task.points_reward,
                total_points=new_balance,
                current_rank=current_rank,
                task_completion_count=user_task.completion_count + 1
            )
                
        except Exception as e:
            return TaskCompleteResponse(
                success=False,
                message=f"任务完成失败：{str(e)}",
                points_earned=0,
                total_points=get_user_points_balance(session=self.session, user_id=user_id),
                current_rank=None,
                task_completion_count=0
            )
    
    def get_leaderboard(self, limit: int = 100, user_id: Optional[uuid.UUID] = None) -> PointsLeaderboardPublic:
        """获取积分排行榜"""
        leaderboard, total, user_rank = get_points_leaderboard(
            session=self.session, limit=limit, user_id=user_id
        )
        
        return PointsLeaderboardPublic(
            data=leaderboard,
            count=total,
            user_rank=user_rank
        )
    
    def get_user_stats(self, user_id: uuid.UUID) -> UserPointsStats:
        """获取用户积分统计"""
        return get_user_points_stats(session=self.session, user_id=user_id)
    
    def get_points_history(
        self, user_id: uuid.UUID, query: PointsHistoryQuery
    ) -> Tuple[List, int, bool]:
        """获取积分历史记录"""
        transactions, total = get_points_transactions(
            session=self.session,
            user_id=user_id,
            skip=(query.page - 1) * query.page_size,
            limit=query.page_size,
            source_type=query.source_type,
            start_date=query.start_date,
            end_date=query.end_date
        )
        
        is_more = (query.page * query.page_size) < total
        return transactions, total, is_more
    
    def get_check_in_history(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Tuple[List, int]:
        """获取签到历史记录"""
        return get_user_check_in_history(
            session=self.session, user_id=user_id, skip=skip, limit=limit
        )
    
    def get_user_tasks(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Tuple[List, int]:
        """获取用户任务列表"""
        return get_user_tasks(
            session=self.session, user_id=user_id, skip=skip, limit=limit
        )
    
    def get_available_tasks(self, skip: int = 0, limit: int = 100) -> Tuple[List, int]:
        """获取可用任务列表"""
        return get_active_tasks(
            session=self.session, skip=skip, limit=limit
        )
    
    def get_available_tasks_with_progress(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List:
        """获取带进度信息的可用任务列表"""
        from app.crud_points import get_active_tasks, get_user_task
        from datetime import datetime, timedelta
        
        # 获取所有活跃任务
        tasks, total = get_active_tasks(session=self.session, skip=skip, limit=limit)
        
        tasks_with_progress = []
        now = datetime.now()
        
        for task in tasks:
            # 获取用户任务记录
            user_task = get_user_task(session=self.session, user_id=user_id, task_id=task.id)
            
            # 初始化进度信息
            current_completion_count = user_task.completion_count if user_task else 0
            remaining_completions = None
            can_complete = True
            cooldown_remaining_hours = None
            status = "in_progress"
            
            # 计算剩余完成次数
            if task.max_completions:
                remaining_completions = max(0, task.max_completions - current_completion_count)
                if remaining_completions <= 0:
                    can_complete = False
                    status = "completed"
            
            # 检查冷却时间
            if task.cooldown_hours and user_task and user_task.last_completed_at:
                cooldown_end = user_task.last_completed_at + timedelta(hours=task.cooldown_hours)
                if now < cooldown_end:
                    can_complete = False
                    cooldown_remaining_hours = int((cooldown_end - now).total_seconds() // 3600)
            
            # 检查任务是否过期
            if task.end_date and now > task.end_date:
                can_complete = False
                status = "expired"
            
            # 检查任务是否开始
            if task.start_date and now < task.start_date:
                can_complete = False
                status = "not_started"
            
            # 构建任务进度信息
            task_with_progress = {
                "task_code": task.task_code,
                "title": task.title,
                "description": task.description,
                "points_reward": task.points_reward,
                "task_type": task.task_type.value,
                "is_active": task.is_active,
                "max_completions": task.max_completions,
                "cooldown_hours": task.cooldown_hours,
                "start_date": task.start_date,
                "end_date": task.end_date,
                "conditions": task.conditions,
                "button_text": task.button_text,
                "uri": task.uri,
                "id": task.id,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "current_completion_count": current_completion_count,
                "remaining_completions": remaining_completions,
                "can_complete": can_complete,
                "cooldown_remaining_hours": cooldown_remaining_hours,
                "status": status
            }
            
            tasks_with_progress.append(task_with_progress)
        
        return tasks_with_progress
    
    def get_monthly_check_in_stats(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> MonthlyCheckInStats:
        """获取月度签到统计"""
        return get_monthly_check_in_stats(
            session=self.session, user_id=user_id, year=year, month=month
        )


def create_points_service(session: Session) -> PointsService:
    """创建积分服务实例"""
    return PointsService(session)
