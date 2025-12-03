"""
抽奖系统CRUD操作
"""
import uuid
import random
from datetime import datetime
from typing import List, Optional, Tuple, Union
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.exc import IntegrityError

from app.models import (
    LotteryActivity, LotteryActivityCreate, LotteryActivityUpdate, LotteryActivityPublic,
    LotteryPrize, LotteryPrizeCreate, LotteryPrizeUpdate, LotteryPrizePublic,
    LotteryRecord, LotteryRecordCreate, LotteryRecordPublic,
    UserPrize, UserPrizeCreate, UserPrizeUpdate, UserPrizePublic,
    User, LotteryActivityStatus, PrizeType, UserPrizeStatus
)
from app.crud_points import get_user_points_balance, update_user_points_balance, create_points_transaction
from app.models import PointsSourceType, PointsTransactionCreate


# ==================== 抽奖活动CRUD ====================

def create_lottery_activity(
    *, session: Session, lottery_activity: LotteryActivityCreate
) -> LotteryActivity:
    """创建抽奖活动"""
    db_activity = LotteryActivity.model_validate(lottery_activity)
    session.add(db_activity)
    session.commit()
    session.refresh(db_activity)
    return db_activity


def get_lottery_activity(
    *, session: Session, activity_id: uuid.UUID
) -> Optional[LotteryActivity]:
    """获取抽奖活动"""
    return session.get(LotteryActivity, activity_id)


def get_lottery_activities(
    *, session: Session, skip: int = 0, limit: int = 100,
    status: Optional[LotteryActivityStatus] = None,
    is_active: Optional[bool] = None
) -> Tuple[List[LotteryActivity], int]:
    """获取抽奖活动列表"""
    conditions = []
    if status is not None:
        conditions.append(LotteryActivity.status == status)
    if is_active is not None:
        conditions.append(LotteryActivity.is_active == is_active)
    
    # 查询活动列表
    query = session.query(LotteryActivity)
    if conditions:
        query = query.filter(and_(*conditions))
    query = query.order_by(desc(LotteryActivity.created_at)).offset(skip).limit(limit)
    
    activities = query.all()
    
    # 查询总数
    count_query = session.query(func.count(LotteryActivity.id))
    if conditions:
        count_query = count_query.filter(and_(*conditions))
    total = count_query.scalar() or 0
    
    return activities, total


def update_lottery_activity(
    *, session: Session, activity_id: uuid.UUID, 
    lottery_activity_update: LotteryActivityUpdate
) -> Optional[LotteryActivity]:
    """更新抽奖活动"""
    db_activity = session.get(LotteryActivity, activity_id)
    if not db_activity:
        return None
    
    update_data = lottery_activity_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_activity, field, value)
    
    db_activity.updated_at = datetime.utcnow()
    session.add(db_activity)
    session.commit()
    session.refresh(db_activity)
    return db_activity


def delete_lottery_activity(*, session: Session, activity_id: uuid.UUID) -> bool:
    """删除抽奖活动"""
    db_activity = session.get(LotteryActivity, activity_id)
    if not db_activity:
        return False
    
    session.delete(db_activity)
    session.commit()
    return True


# ==================== 抽奖奖品CRUD ====================

def create_lottery_prize(
    *, session: Session, lottery_prize: LotteryPrizeCreate
) -> LotteryPrize:
    """创建抽奖奖品"""
    db_prize = LotteryPrize.model_validate(lottery_prize)
    session.add(db_prize)
    session.commit()
    session.refresh(db_prize)
    return db_prize


def get_lottery_prize(
    *, session: Session, prize_id: uuid.UUID
) -> Optional[LotteryPrize]:
    """获取抽奖奖品"""
    return session.get(LotteryPrize, prize_id)


def get_lottery_prizes_by_activity(
    *, session: Session, activity_id: uuid.UUID,
    skip: int = 0, limit: int = 100,
    is_active: Optional[bool] = None
) -> Tuple[List[LotteryPrize], int]:
    """获取活动的奖品列表"""
    conditions = [LotteryPrize.activity_id == activity_id]
    if is_active is not None:
        conditions.append(LotteryPrize.is_active == is_active)
    
    # 查询奖品列表
    query = session.query(LotteryPrize).filter(and_(*conditions))
    query = query.order_by(LotteryPrize.sort_order.asc(), LotteryPrize.created_at.asc())
    query = query.offset(skip).limit(limit)
    
    prizes = query.all()
    
    # 查询总数
    count_query = session.query(func.count(LotteryPrize.id)).filter(and_(*conditions))
    total = count_query.scalar() or 0
    
    return prizes, total


def update_lottery_prize(
    *, session: Session, prize_id: uuid.UUID,
    lottery_prize_update: LotteryPrizeUpdate
) -> Optional[LotteryPrize]:
    """更新抽奖奖品"""
    db_prize = session.get(LotteryPrize, prize_id)
    if not db_prize:
        return None
    
    update_data = lottery_prize_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_prize, field, value)
    
    db_prize.updated_at = datetime.utcnow()
    session.add(db_prize)
    session.commit()
    session.refresh(db_prize)
    return db_prize


def delete_lottery_prize(*, session: Session, prize_id: uuid.UUID) -> bool:
    """删除抽奖奖品"""
    db_prize = session.get(LotteryPrize, prize_id)
    if not db_prize:
        return False
    
    session.delete(db_prize)
    session.commit()
    return True


# ==================== 抽奖记录CRUD ====================

def create_lottery_record(
    *, session: Session, lottery_record: LotteryRecordCreate
) -> LotteryRecord:
    """创建抽奖记录"""
    db_record = LotteryRecord.model_validate(lottery_record)
    session.add(db_record)
    session.commit()
    session.refresh(db_record)
    return db_record


def get_user_lottery_records(
    *, session: Session, user_id: uuid.UUID,
    activity_id: Optional[uuid.UUID] = None,
    skip: int = 0, limit: int = 100
) -> Tuple[List[LotteryRecord], int]:
    """获取用户抽奖记录"""
    conditions = [LotteryRecord.user_id == user_id]
    if activity_id is not None:
        conditions.append(LotteryRecord.activity_id == activity_id)
    
    # 查询记录列表
    query = session.query(LotteryRecord).filter(and_(*conditions))
    query = query.order_by(desc(LotteryRecord.created_at)).offset(skip).limit(limit)
    
    records = query.all()
    
    # 查询总数
    count_query = session.query(func.count(LotteryRecord.id)).filter(and_(*conditions))
    total = count_query.scalar() or 0
    
    return records, total


def get_user_draw_count(
    *, session: Session, user_id: uuid.UUID, activity_id: uuid.UUID
) -> int:
    """获取用户在某个活动中的抽奖次数"""
    query = session.query(func.count(LotteryRecord.id)).filter(
        and_(
            LotteryRecord.user_id == user_id,
            LotteryRecord.activity_id == activity_id
        )
    )
    return query.scalar() or 0


# ==================== 用户奖品CRUD ====================

def create_user_prize(
    *, session: Session, user_prize: UserPrizeCreate
) -> UserPrize:
    """创建用户奖品"""
    db_user_prize = UserPrize.model_validate(user_prize)
    session.add(db_user_prize)
    session.commit()
    session.refresh(db_user_prize)
    return db_user_prize


def get_user_prizes(
    *, session: Session, user_id: uuid.UUID,
    status: Optional[UserPrizeStatus] = None,
    skip: int = 0, limit: int = 100
) -> Tuple[List[UserPrize], int]:
    """获取用户奖品列表"""
    conditions = [UserPrize.user_id == user_id]
    if status is not None:
        conditions.append(UserPrize.status == status)
    
    # 查询奖品列表
    query = session.query(UserPrize).filter(and_(*conditions))
    query = query.order_by(desc(UserPrize.created_at)).offset(skip).limit(limit)
    
    prizes = query.all()
    
    # 查询总数
    count_query = session.query(func.count(UserPrize.id)).filter(and_(*conditions))
    total = count_query.scalar() or 0
    
    return prizes, total


def update_user_prize(
    *, session: Session, user_prize_id: uuid.UUID,
    user_prize_update: UserPrizeUpdate
) -> Optional[UserPrize]:
    """更新用户奖品状态"""
    db_user_prize = session.get(UserPrize, user_prize_id)
    if not db_user_prize:
        return None
    
    update_data = user_prize_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user_prize, field, value)
    
    db_user_prize.updated_at = datetime.utcnow()
    session.add(db_user_prize)
    session.commit()
    session.refresh(db_user_prize)
    return db_user_prize


# ==================== 抽奖业务逻辑 ====================

def get_available_prizes(
    *, session: Session, activity_id: uuid.UUID
) -> List[LotteryPrize]:
    """获取可抽奖的奖品列表（有库存且激活的）"""
    query = session.query(LotteryPrize).filter(
        and_(
            LotteryPrize.activity_id == activity_id,
            LotteryPrize.is_active == True,
            LotteryPrize.quantity > 0
        )
    ).order_by(LotteryPrize.sort_order.asc())
    
    return query.all()


def calculate_prize_probabilities(prizes: List[LotteryPrize]) -> List[LotteryPrize]:
    """计算奖品概率（基于权重）"""
    if not prizes:
        return prizes
    
    total_weight = sum(prize.weight for prize in prizes)
    if total_weight == 0:
        return prizes
    
    # 注意：这里不再设置probability字段，因为我们已经移除了它
    # 概率计算在draw_prize函数中直接基于权重进行
    return prizes


def draw_prize(*, session: Session, prizes: List[LotteryPrize]) -> Optional[LotteryPrize]:
    """执行抽奖逻辑"""
    if not prizes:
        return None
    
    # 使用权重随机选择奖品
    total_weight = sum(prize.weight for prize in prizes)
    if total_weight == 0:
        return None
    
    random_value = random.uniform(0, total_weight)
    current_weight = 0
    
    for prize in prizes:
        current_weight += prize.weight
        if random_value <= current_weight:
            return prize
    
    # 如果随机值超出范围，返回最后一个奖品
    return prizes[-1]


def process_prize_draw(
    *, session: Session, user_id: uuid.UUID, activity_id: uuid.UUID
) -> Tuple[Optional[LotteryPrize], str]:
    """处理抽奖流程"""
    # 1. 检查活动是否存在且有效
    activity = get_lottery_activity(session=session, activity_id=activity_id)
    if not activity:
        return None, "活动不存在"
    
    if not activity.is_active or activity.status != LotteryActivityStatus.ACTIVE:
        return None, "活动未开始或已结束"
    
    now = datetime.utcnow()
    if now < activity.start_time or now > activity.end_time:
        return None, "活动时间未到或已结束"
    
    # 2. 检查用户抽奖次数限制
    if activity.max_draws_per_user:
        user_draw_count = get_user_draw_count(
            session=session, user_id=user_id, activity_id=activity_id
        )
        if user_draw_count >= activity.max_draws_per_user:
            return None, f"已达到最大抽奖次数限制（{activity.max_draws_per_user}次）"
    
    # 3. 检查用户积分是否足够
    if activity.points_cost > 0:
        user_balance = get_user_points_balance(session=session, user_id=user_id)
        if user_balance < activity.points_cost:
            return None, f"积分不足，需要{activity.points_cost}积分"
    
    # 4. 获取可抽奖的奖品
    available_prizes = get_available_prizes(session=session, activity_id=activity_id)
    if not available_prizes:
        return None, "暂无可抽奖的奖品"
    
    # 5. 执行抽奖
    drawn_prize = draw_prize(session=session, prizes=available_prizes)
    if not drawn_prize:
        return None, "抽奖失败"
    
    # 6. 扣除积分
    if activity.points_cost > 0:
        current_balance = get_user_points_balance(session=session, user_id=user_id)
        new_balance = current_balance - activity.points_cost
        update_user_points_balance(
            session=session, user_id=user_id, new_balance=new_balance
        )
        
        # 记录积分流水
        transaction = PointsTransactionCreate(
            user_id=user_id,
            points_change=-activity.points_cost,
            balance_after=new_balance,
            source_type=PointsSourceType.CHECK_IN,  # 可以新增LOTTERY类型
            source_id=str(activity_id),
            description=f"抽奖消耗积分：{activity.name}"
        )
        create_points_transaction(session=session, points_transaction=transaction)
    
    # 7. 减少奖品库存
    drawn_prize.quantity -= 1
    session.add(drawn_prize)
    
    # 8. 创建抽奖记录
    record = LotteryRecordCreate(
        user_id=user_id,
        activity_id=activity_id,
        prize_id=drawn_prize.id,
        prize_name_snapshot=drawn_prize.name,
        prize_type_snapshot=drawn_prize.prize_type,
        points_cost=activity.points_cost
    )
    create_lottery_record(session=session, lottery_record=record)
    
    # 9. 创建用户奖品记录（如果不是谢谢参与）
    if drawn_prize.prize_type != PrizeType.THANK_YOU:
        user_prize = UserPrizeCreate(
            user_id=user_id,
            prize_id=drawn_prize.id,
            status=UserPrizeStatus.PENDING
        )
        create_user_prize(session=session, user_prize=user_prize)
        
        # 如果是积分奖品，直接发放
        if drawn_prize.prize_type == PrizeType.POINTS and drawn_prize.points_value:
            current_balance = get_user_points_balance(session=session, user_id=user_id)
            new_balance = current_balance + drawn_prize.points_value
            update_user_points_balance(
                session=session, user_id=user_id, new_balance=new_balance
            )
            
            # 记录积分流水
            transaction = PointsTransactionCreate(
                user_id=user_id,
                points_change=drawn_prize.points_value,
                balance_after=new_balance,
                source_type=PointsSourceType.CHECK_IN,  # 可以新增LOTTERY类型
                source_id=str(drawn_prize.id),
                description=f"抽奖获得积分：{drawn_prize.name}"
            )
            create_points_transaction(session=session, points_transaction=transaction)
            
            # 更新用户奖品状态为已领取
            user_prize_record = session.query(UserPrize).filter(
                and_(
                    UserPrize.user_id == user_id,
                    UserPrize.prize_id == drawn_prize.id
                )
            ).order_by(desc(UserPrize.created_at)).first()
            
            if user_prize_record:
                user_prize_record.status = UserPrizeStatus.CLAIMED
                user_prize_record.claimed_at = datetime.utcnow()
                session.add(user_prize_record)
    
    session.commit()
    return drawn_prize, "抽奖成功"


def get_activity_statistics(
    *, session: Session, activity_id: uuid.UUID
) -> dict:
    """获取活动统计信息"""
    activity = get_lottery_activity(session=session, activity_id=activity_id)
    if not activity:
        return {}
    
    # 奖品数量
    prize_count = session.query(func.count(LotteryPrize.id)).filter(
        LotteryPrize.activity_id == activity_id
    ).scalar() or 0
    
    # 总抽奖次数
    total_draws = session.query(func.count(LotteryRecord.id)).filter(
        LotteryRecord.activity_id == activity_id
    ).scalar() or 0
    
    # 参与用户数
    unique_users = session.query(func.count(func.distinct(LotteryRecord.user_id))).filter(
        LotteryRecord.activity_id == activity_id
    ).scalar() or 0
    
    return {
        "activity_id": activity_id,
        "prize_count": prize_count,
        "total_draws": total_draws,
        "unique_users": unique_users,
        "status": activity.status,
        "is_active": activity.is_active
    }
