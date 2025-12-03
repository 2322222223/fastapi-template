"""盲盒抽奖系统业务逻辑服务"""
import uuid
import random
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session
from app.models import (
    RechargeOrder, RechargeOrderCreate, RechargeOrderStatus, RechargeType,
    UserBlindBox, UserBlindBoxCreate, BlindBoxStatus,
    PrizeTemplate, BlindBoxUserPrize, BlindBoxUserPrizeCreate,
    PrizeRedemptionStatus, BlindBoxPrizeType, User
)
from app import crud_blindbox
from app.crud_points import create_points_transaction
from app.models import PointsTransactionCreate, PointsSourceType
import json


class BlindBoxService:
    """盲盒抽奖业务服务类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_recharge_order(
        self, 
        user_id: uuid.UUID,
        recharge_type: RechargeType,
        phone_number: str,
        amount: int,
        user_latitude: Optional[float] = None,
        user_longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        创建充值订单
        
        Args:
            user_id: 用户ID
            recharge_type: 充值类型
            phone_number: 充值手机号
            amount: 充值金额（分）
            user_latitude: 用户纬度
            user_longitude: 用户经度
        
        Returns:
            包含订单信息和盲盒状态的字典
        """
        # 检查是否在商圈内（暂时简化，后续可以实现实际的地理位置判断）
        business_district_id = None
        is_eligible_for_prize = False
        
        if user_latitude and user_longitude:
            # TODO: 实现实际的商圈检测逻辑
            # district = crud_blindbox.check_if_in_business_district(
            #     session=self.session,
            #     latitude=user_latitude,
            #     longitude=user_longitude
            # )
            # if district:
            #     business_district_id = district.id
            #     is_eligible_for_prize = True
            
            # 暂时默认在商圈内（用于测试）
            is_eligible_for_prize = True
        
        # 创建充值订单
        order_create = RechargeOrderCreate(
            recharge_type=recharge_type,
            phone_number=phone_number,
            amount=amount,
            user_latitude=user_latitude,
            user_longitude=user_longitude
        )
        
        order = crud_blindbox.create_recharge_order(
            session=self.session,
            order=order_create,
            user_id=user_id
        )
        
        # 更新订单的盲盒资格和商圈信息
        from app.crud_blindbox import update_recharge_order
        from app.models import RechargeOrderUpdate
        
        order_update = RechargeOrderUpdate(
            is_eligible_for_prize=is_eligible_for_prize,
            business_district_id=business_district_id
        )
        order = update_recharge_order(
            session=self.session,
            order_id=order.id,
            order_update=order_update
        )
        
        return {
            "order": order,
            "is_eligible_for_prize": is_eligible_for_prize,
            "message": "充值订单创建成功" + ("，获得抽奖资格" if is_eligible_for_prize else "")
        }
    
    def process_recharge_success(self, order_id: uuid.UUID) -> Dict[str, Any]:
        """
        处理充值成功（假接口）
        
        Args:
            order_id: 订单ID
        
        Returns:
            处理结果和盲盒信息
        """
        order = crud_blindbox.get_recharge_order(session=self.session, order_id=order_id)
        if not order:
            return {"success": False, "message": "订单不存在"}
        
        # 更新订单状态
        from app.crud_blindbox import update_recharge_order
        from app.models import RechargeOrderUpdate
        
        order_update = RechargeOrderUpdate(
            status=RechargeOrderStatus.SUCCESS,
            paid_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        order = update_recharge_order(
            session=self.session,
            order_id=order_id,
            order_update=order_update
        )
        
        # 如果有资格获得盲盒，则创建盲盒
        blind_box = None
        if order.is_eligible_for_prize:
            blind_box_create = UserBlindBoxCreate(
                user_id=order.user_id,
                recharge_order_id=order.id,
                expired_at=datetime.utcnow() + timedelta(days=7)  # 7天有效期
            )
            blind_box = crud_blindbox.create_blind_box(
                session=self.session,
                blind_box=blind_box_create
            )
        
        return {
            "success": True,
            "message": "充值成功" + ("，获得盲盒一个" if blind_box else ""),
            "order": order,
            "blind_box": blind_box
        }
    
    def draw_prize(self) -> Optional[PrizeTemplate]:
        """
        抽奖逻辑 - 根据概率随机抽取奖品
        
        Returns:
            抽中的奖品模板
        """
        # 获取所有可用奖品
        prizes, _ = crud_blindbox.get_active_prize_templates(
            session=self.session,
            skip=0,
            limit=100
        )
        
        if not prizes:
            return None
        
        # 过滤掉库存不足的奖品
        available_prizes = []
        for prize in prizes:
            if prize.stock is None or prize.stock > 0:
                available_prizes.append(prize)
        
        if not available_prizes:
            return None
        
        # 归一化概率
        total_probability = sum(p.probability for p in available_prizes)
        if total_probability <= 0:
            return None
        
        # 随机抽取
        rand = random.uniform(0, total_probability)
        cumulative = 0
        
        for prize in available_prizes:
            cumulative += prize.probability
            if rand <= cumulative:
                return prize
        
        # 兜底返回最后一个
        return available_prizes[-1]
    
    def open_blind_box(self, user_id: uuid.UUID, blind_box_id: uuid.UUID) -> Dict[str, Any]:
        """
        开启盲盒
        
        Args:
            user_id: 用户ID
            blind_box_id: 盲盒ID
        
        Returns:
            开启结果和获得的奖品
        """
        # 获取盲盒
        blind_box = crud_blindbox.get_blind_box(session=self.session, blind_box_id=blind_box_id)
        if not blind_box:
            return {"success": False, "message": "盲盒不存在"}
        
        # 检查所有权
        if blind_box.user_id != user_id:
            return {"success": False, "message": "无权开启此盲盒"}
        
        # 检查状态
        if blind_box.status != BlindBoxStatus.UNOPENED:
            return {"success": False, "message": "盲盒已开启或已过期"}
        
        # 检查是否过期
        if blind_box.expired_at and blind_box.expired_at < datetime.utcnow():
            # 更新为过期状态
            blind_box.status = BlindBoxStatus.EXPIRED
            blind_box.updated_at = datetime.utcnow()
            self.session.add(blind_box)
            self.session.commit()
            return {"success": False, "message": "盲盒已过期"}
        
        # 抽奖
        prize_template = self.draw_prize()
        if not prize_template:
            return {"success": False, "message": "抽奖失败，暂无可用奖品"}
        
        # 减少库存
        if not crud_blindbox.decrease_prize_stock(session=self.session, prize_id=prize_template.id):
            return {"success": False, "message": "奖品库存不足"}
        
        # 开启盲盒
        blind_box = crud_blindbox.open_blind_box(session=self.session, blind_box_id=blind_box_id)
        if not blind_box:
            return {"success": False, "message": "开启盲盒失败"}
        
        # 生成兑换码（仅对需要兑换的奖品）
        redemption_code = None
        expired_at = None
        
        if prize_template.prize_type not in [BlindBoxPrizeType.POINTS, BlindBoxPrizeType.THANK_YOU]:
            redemption_code = f"{prize_template.prize_code[:4]}{datetime.now().strftime('%m%d')}{str(uuid.uuid4())[:6].upper()}"
        
        if prize_template.validity_days:
            expired_at = datetime.utcnow() + timedelta(days=prize_template.validity_days)
        
        # 创建用户奖品记录
        user_prize_create = BlindBoxUserPrizeCreate(
            user_id=user_id,
            blind_box_id=blind_box_id,
            prize_template_id=prize_template.id,
            redemption_code=redemption_code,
            expired_at=expired_at
        )
        
        user_prize = crud_blindbox.create_user_prize(
            session=self.session,
            prize=user_prize_create
        )
        
        # 如果是积分奖品，自动发放积分
        if prize_template.prize_type == BlindBoxPrizeType.POINTS:
            try:
                config = json.loads(prize_template.config or "{}")
                points_amount = config.get("points_amount", 0)
                
                if points_amount > 0:
                    # 创建积分交易记录
                    points_transaction = PointsTransactionCreate(
                        user_id=user_id,
                        points_change=points_amount,
                        source_type=PointsSourceType.TASK_COMPLETE,
                        source_id=str(blind_box_id),
                        description=f"开盲盒获得 {points_amount} 积分"
                    )
                    create_points_transaction(
                        session=self.session,
                        transaction=points_transaction
                    )
                    
                    # 更新奖品状态为已兑换
                    user_prize.redemption_status = PrizeRedemptionStatus.REDEEMED
                    user_prize.redeemed_at = datetime.utcnow()
                    self.session.add(user_prize)
                    self.session.commit()
                    self.session.refresh(user_prize)
            except Exception as e:
                print(f"发放积分失败: {e}")
        
        return {
            "success": True,
            "message": f"恭喜获得 {prize_template.name}",
            "prize": {
                "id": user_prize.id,
                "prize_name": prize_template.name,
                "prize_type": prize_template.prize_type.value,
                "prize_value": prize_template.prize_value,
                "prize_image_url": prize_template.image_url,
                "redemption_code": redemption_code,
                "redemption_instructions": prize_template.redemption_instructions,
                "redemption_status": user_prize.redemption_status.value,
                "expired_at": expired_at,
                "created_at": user_prize.created_at
            }
        }
    
    def get_user_blind_box_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """获取用户盲盒统计信息"""
        _, total, unopened, opened = crud_blindbox.get_user_blind_boxes(
            session=self.session,
            user_id=user_id,
            skip=0,
            limit=1
        )
        
        _, prize_total, unredeemed, redeemed = crud_blindbox.get_user_prizes(
            session=self.session,
            user_id=user_id,
            skip=0,
            limit=1
        )
        
        return {
            "total_blind_boxes": total,
            "unopened_count": unopened,
            "opened_count": opened,
            "total_prizes": prize_total,
            "unredeemed_prizes": unredeemed,
            "redeemed_prizes": redeemed
        }


def create_blindbox_service(session: Session) -> BlindBoxService:
    """创建盲盒服务实例"""
    return BlindBoxService(session)

