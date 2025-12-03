"""盲盒抽奖系统 CRUD 操作"""
import uuid
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from sqlmodel import Session, select, func, or_, and_
from app.models import (
    RechargeOrder, RechargeOrderCreate, RechargeOrderUpdate, RechargeOrderStatus,
    UserBlindBox, UserBlindBoxCreate, BlindBoxStatus,
    PrizeTemplate, PrizeTemplateCreate, PrizeTemplateUpdate,
    BlindBoxUserPrize, BlindBoxUserPrizeCreate, BlindBoxUserPrizeUpdate,
    PrizeRedemptionStatus, BusinessDistrict
)
import math


# ==================== 充值订单 CRUD ====================

def create_recharge_order(*, session: Session, order: RechargeOrderCreate, user_id: uuid.UUID) -> RechargeOrder:
    """创建充值订单"""
    # 生成订单号
    order_no = f"RO{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8].upper()}"
    
    db_obj = RechargeOrder(
        **order.model_dump(),
        user_id=user_id,
        order_no=order_no
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_recharge_order(*, session: Session, order_id: uuid.UUID) -> Optional[RechargeOrder]:
    """根据ID获取充值订单"""
    return session.get(RechargeOrder, order_id)


def get_recharge_order_by_order_no(*, session: Session, order_no: str) -> Optional[RechargeOrder]:
    """根据订单号获取充值订单"""
    statement = select(RechargeOrder).where(RechargeOrder.order_no == order_no)
    return session.exec(statement).first()


def get_user_recharge_orders(
    *, session: Session, user_id: uuid.UUID, 
    skip: int = 0, limit: int = 20
) -> Tuple[List[RechargeOrder], int]:
    """获取用户的充值订单列表"""
    # 查询订单
    statement = select(RechargeOrder).where(
        RechargeOrder.user_id == user_id
    ).order_by(RechargeOrder.created_at.desc()).offset(skip).limit(limit)
    
    orders = session.exec(statement).all()
    
    # 查询总数
    count_statement = select(func.count(RechargeOrder.id)).where(
        RechargeOrder.user_id == user_id
    )
    total = session.exec(count_statement).one()
    
    return list(orders), total


def update_recharge_order(
    *, session: Session, order_id: uuid.UUID, 
    order_update: RechargeOrderUpdate
) -> Optional[RechargeOrder]:
    """更新充值订单"""
    db_obj = session.get(RechargeOrder, order_id)
    if not db_obj:
        return None
    
    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db_obj.updated_at = datetime.utcnow()
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def check_if_in_business_district(
    *, session: Session, latitude: float, longitude: float
) -> Optional[BusinessDistrict]:
    """检查用户位置是否在商圈范围内"""
    # 获取所有激活的商圈
    statement = select(BusinessDistrict)  # 注意：这里使用的是现有的 BusinessDistrict 模型
    districts = session.exec(statement).all()
    
    for district in districts:
        # 简单的球面距离计算（Haversine公式）
        # 将经纬度转换为弧度
        lat1_rad = math.radians(latitude)
        lon1_rad = math.radians(longitude)
        # 商圈中心坐标 - BusinessDistrict模型没有 latitude/longitude 字段
        # 需要根据实际的 BusinessDistrict 结构调整
        # 暂时返回 None，需要用户确认如何判断是否在商圈内
        pass
    
    return None


# ==================== 盲盒 CRUD ====================

def create_blind_box(*, session: Session, blind_box: UserBlindBoxCreate) -> UserBlindBox:
    """创建盲盒"""
    db_obj = UserBlindBox(**blind_box.model_dump())
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_blind_box(*, session: Session, blind_box_id: uuid.UUID) -> Optional[UserBlindBox]:
    """根据ID获取盲盒"""
    return session.get(UserBlindBox, blind_box_id)


def get_user_blind_boxes(
    *, session: Session, user_id: uuid.UUID,
    status: Optional[BlindBoxStatus] = None,
    skip: int = 0, limit: int = 20
) -> Tuple[List[UserBlindBox], int]:
    """获取用户的盲盒列表"""
    # 构建查询条件
    conditions = [UserBlindBox.user_id == user_id]
    if status:
        conditions.append(UserBlindBox.status == status)
    
    # 查询盲盒
    statement = select(UserBlindBox).where(
        *conditions
    ).order_by(UserBlindBox.created_at.desc()).offset(skip).limit(limit)
    
    blind_boxes = session.exec(statement).all()
    
    # 查询总数
    count_statement = select(func.count(UserBlindBox.id)).where(*conditions)
    total = session.exec(count_statement).one()
    
    # 统计未开启和已开启数量
    unopened_statement = select(func.count(UserBlindBox.id)).where(
        UserBlindBox.user_id == user_id,
        UserBlindBox.status == BlindBoxStatus.UNOPENED
    )
    unopened_count = session.exec(unopened_statement).one()
    
    opened_statement = select(func.count(UserBlindBox.id)).where(
        UserBlindBox.user_id == user_id,
        UserBlindBox.status == BlindBoxStatus.OPENED
    )
    opened_count = session.exec(opened_statement).one()
    
    return list(blind_boxes), total, unopened_count, opened_count


def open_blind_box(*, session: Session, blind_box_id: uuid.UUID) -> Optional[UserBlindBox]:
    """开启盲盒"""
    db_obj = session.get(UserBlindBox, blind_box_id)
    if not db_obj:
        return None
    
    if db_obj.status != BlindBoxStatus.UNOPENED:
        return None  # 已经开启或过期
    
    db_obj.status = BlindBoxStatus.OPENED
    db_obj.opened_at = datetime.utcnow()
    db_obj.updated_at = datetime.utcnow()
    
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


# ==================== 奖品模板 CRUD ====================

def create_prize_template(*, session: Session, prize: PrizeTemplateCreate) -> PrizeTemplate:
    """创建奖品模板"""
    db_obj = PrizeTemplate(**prize.model_dump())
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_prize_template(*, session: Session, prize_id: uuid.UUID) -> Optional[PrizeTemplate]:
    """根据ID获取奖品模板"""
    return session.get(PrizeTemplate, prize_id)


def get_prize_template_by_code(*, session: Session, prize_code: str) -> Optional[PrizeTemplate]:
    """根据代码获取奖品模板"""
    statement = select(PrizeTemplate).where(PrizeTemplate.prize_code == prize_code)
    return session.exec(statement).first()


def get_active_prize_templates(
    *, session: Session, skip: int = 0, limit: int = 100
) -> Tuple[List[PrizeTemplate], int]:
    """获取可用的奖品模板列表"""
    # 查询奖品
    statement = select(PrizeTemplate).where(
        PrizeTemplate.is_active == True
    ).order_by(PrizeTemplate.probability.desc()).offset(skip).limit(limit)
    
    prizes = session.exec(statement).all()
    
    # 查询总数
    count_statement = select(func.count(PrizeTemplate.id)).where(
        PrizeTemplate.is_active == True
    )
    total = session.exec(count_statement).one()
    
    return list(prizes), total


def update_prize_template(
    *, session: Session, prize_id: uuid.UUID, 
    prize_update: PrizeTemplateUpdate
) -> Optional[PrizeTemplate]:
    """更新奖品模板"""
    db_obj = session.get(PrizeTemplate, prize_id)
    if not db_obj:
        return None
    
    update_data = prize_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db_obj.updated_at = datetime.utcnow()
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def decrease_prize_stock(*, session: Session, prize_id: uuid.UUID) -> bool:
    """减少奖品库存"""
    db_obj = session.get(PrizeTemplate, prize_id)
    if not db_obj or not db_obj.stock:
        return True  # 无限库存
    
    if db_obj.stock <= 0:
        return False  # 库存不足
    
    db_obj.stock -= 1
    db_obj.updated_at = datetime.utcnow()
    session.add(db_obj)
    session.commit()
    return True


# ==================== 用户奖品 CRUD ====================

def create_user_prize(*, session: Session, prize: BlindBoxUserPrizeCreate) -> BlindBoxUserPrize:
    """创建用户奖品"""
    db_obj = BlindBoxUserPrize(**prize.model_dump())
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_user_prize(*, session: Session, prize_id: uuid.UUID) -> Optional[BlindBoxUserPrize]:
    """根据ID获取用户奖品"""
    return session.get(BlindBoxUserPrize, prize_id)


def get_user_prize_by_blind_box(*, session: Session, blind_box_id: uuid.UUID) -> Optional[BlindBoxUserPrize]:
    """根据盲盒ID获取用户奖品"""
    statement = select(BlindBoxUserPrize).where(BlindBoxUserPrize.blind_box_id == blind_box_id)
    return session.exec(statement).first()


def get_user_prizes(
    *, session: Session, user_id: uuid.UUID,
    redemption_status: Optional[PrizeRedemptionStatus] = None,
    skip: int = 0, limit: int = 20
) -> Tuple[List[BlindBoxUserPrize], int, int, int]:
    """获取用户的奖品列表"""
    # 构建查询条件
    conditions = [BlindBoxUserPrize.user_id == user_id]
    if redemption_status:
        conditions.append(BlindBoxUserPrize.redemption_status == redemption_status)
    
    # 查询奖品
    statement = select(BlindBoxUserPrize).where(
        *conditions
    ).order_by(BlindBoxUserPrize.created_at.desc()).offset(skip).limit(limit)
    
    prizes = session.exec(statement).all()
    
    # 查询总数
    count_statement = select(func.count(BlindBoxUserPrize.id)).where(*conditions)
    total = session.exec(count_statement).one()
    
    # 统计未兑换和已兑换数量
    unredeemed_statement = select(func.count(BlindBoxUserPrize.id)).where(
        BlindBoxUserPrize.user_id == user_id,
        BlindBoxUserPrize.redemption_status == PrizeRedemptionStatus.UNREDEEMED
    )
    unredeemed_count = session.exec(unredeemed_statement).one()
    
    redeemed_statement = select(func.count(BlindBoxUserPrize.id)).where(
        BlindBoxUserPrize.user_id == user_id,
        BlindBoxUserPrize.redemption_status.in_([
            PrizeRedemptionStatus.REDEEMED,
            PrizeRedemptionStatus.USED
        ])
    )
    redeemed_count = session.exec(redeemed_statement).one()
    
    return list(prizes), total, unredeemed_count, redeemed_count


def update_user_prize(
    *, session: Session, prize_id: uuid.UUID, 
    prize_update: BlindBoxUserPrizeUpdate
) -> Optional[BlindBoxUserPrize]:
    """更新用户奖品"""
    db_obj = session.get(BlindBoxUserPrize, prize_id)
    if not db_obj:
        return None
    
    update_data = prize_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    db_obj.updated_at = datetime.utcnow()
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def redeem_user_prize(*, session: Session, prize_id: uuid.UUID) -> Optional[BlindBoxUserPrize]:
    """兑换用户奖品"""
    db_obj = session.get(BlindBoxUserPrize, prize_id)
    if not db_obj:
        return None
    
    if db_obj.redemption_status != PrizeRedemptionStatus.UNREDEEMED:
        return None  # 已经兑换
    
    db_obj.redemption_status = PrizeRedemptionStatus.REDEEMED
    db_obj.redeemed_at = datetime.utcnow()
    db_obj.updated_at = datetime.utcnow()
    
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

