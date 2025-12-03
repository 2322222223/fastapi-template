"""盲盒抽奖系统API路由"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from app.api.deps import get_current_user, get_db
from app.models import (
    User, RechargeType, BlindBoxStatus, PrizeRedemptionStatus,
    RechargeOrderCreate, RechargeOrderPublic, RechargeOrdersPublic,
    UserBlindBoxPublic, UserBlindBoxesPublic,
    BlindBoxUserPrizePublic, BlindBoxUserPrizesPublic,
    BlindBoxStats, OpenBlindBoxRequest, OpenBlindBoxResponse
)
from app.services_blindbox import create_blindbox_service
from app import crud_blindbox
from pydantic import BaseModel

router = APIRouter()


# ==================== 响应模型 ====================

class RechargeOrderResponse(BaseModel):
    """充值订单响应"""
    success: bool
    message: str
    data: Optional[RechargeOrderPublic] = None
    is_eligible_for_prize: bool = False


class ProcessRechargeResponse(BaseModel):
    """处理充值响应"""
    success: bool
    message: str
    order: Optional[RechargeOrderPublic] = None
    blind_box: Optional[UserBlindBoxPublic] = None


# ==================== 充值相关接口 ====================

@router.post("/recharge/create", response_model=RechargeOrderResponse)
def create_recharge_order(
    recharge_type: RechargeType,
    phone_number: str,
    amount: int,
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RechargeOrderResponse:
    """
    创建充值订单
    
    - **recharge_type**: 充值类型（mobile/data）
    - **phone_number**: 充值手机号
    - **amount**: 充值金额（分）
    - **user_latitude**: 用户纬度（可选，用于判断是否在商圈内）
    - **user_longitude**: 用户经度（可选，用于判断是否在商圈内）
    """
    service = create_blindbox_service(db)
    result = service.create_recharge_order(
        user_id=current_user.id,
        recharge_type=recharge_type,
        phone_number=phone_number,
        amount=amount,
        user_latitude=user_latitude,
        user_longitude=user_longitude
    )
    
    return RechargeOrderResponse(
        success=True,
        message=result["message"],
        data=RechargeOrderPublic.model_validate(result["order"]),
        is_eligible_for_prize=result["is_eligible_for_prize"]
    )


@router.post("/recharge/{order_id}/process", response_model=ProcessRechargeResponse)
def process_recharge(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ProcessRechargeResponse:
    """
    处理充值成功（模拟接口）
    
    实际使用时，此接口应该由充值回调触发
    """
    service = create_blindbox_service(db)
    result = service.process_recharge_success(order_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    order_data = RechargeOrderPublic.model_validate(result["order"]) if result.get("order") else None
    blind_box_data = UserBlindBoxPublic.model_validate(result["blind_box"]) if result.get("blind_box") else None
    
    return ProcessRechargeResponse(
        success=True,
        message=result["message"],
        order=order_data,
        blind_box=blind_box_data
    )


@router.get("/recharge/my-orders", response_model=RechargeOrdersPublic)
def get_my_recharge_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RechargeOrdersPublic:
    """获取我的充值订单列表"""
    skip = (page - 1) * page_size
    
    orders, total = crud_blindbox.get_user_recharge_orders(
        session=db,
        user_id=current_user.id,
        skip=skip,
        limit=page_size
    )
    
    orders_data = [RechargeOrderPublic.model_validate(order) for order in orders]
    
    return RechargeOrdersPublic(
        data=orders_data,
        total=total,
        page=page,
        page_size=page_size
    )


# ==================== 盲盒相关接口 ====================

@router.get("/blind-boxes/my", response_model=UserBlindBoxesPublic)
def get_my_blind_boxes(
    status: Optional[BlindBoxStatus] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserBlindBoxesPublic:
    """
    获取我的盲盒列表
    
    - **status**: 盲盒状态筛选（可选）
    """
    skip = (page - 1) * page_size
    
    blind_boxes, total, unopened_count, opened_count = crud_blindbox.get_user_blind_boxes(
        session=db,
        user_id=current_user.id,
        status=status,
        skip=skip,
        limit=page_size
    )
    
    # 组装响应数据
    blind_boxes_data = []
    for box in blind_boxes:
        box_dict = box.model_dump()
        # 添加充值订单信息
        if box.recharge_order:
            box_dict["recharge_order_no"] = box.recharge_order.order_no
            box_dict["recharge_amount"] = box.recharge_order.amount
            box_dict["recharge_type"] = box.recharge_order.recharge_type.value
        
        blind_boxes_data.append(UserBlindBoxPublic(**box_dict))
    
    return UserBlindBoxesPublic(
        data=blind_boxes_data,
        total=total,
        unopened_count=unopened_count,
        opened_count=opened_count
    )


@router.post("/blind-boxes/open", response_model=OpenBlindBoxResponse)
def open_blind_box(
    request: OpenBlindBoxRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> OpenBlindBoxResponse:
    """
    开启盲盒
    
    - **blind_box_id**: 盲盒ID
    """
    service = create_blindbox_service(db)
    result = service.open_blind_box(
        user_id=current_user.id,
        blind_box_id=request.blind_box_id
    )
    
    if not result["success"]:
        return OpenBlindBoxResponse(
            success=False,
            message=result["message"],
            data=None
        )
    
    prize_data = result["prize"]
    prize_public = BlindBoxUserPrizePublic(
        id=prize_data["id"],
        user_id=current_user.id,
        blind_box_id=request.blind_box_id,
        prize_template_id=uuid.uuid4(),  # 临时，实际从数据库获取
        redemption_status=PrizeRedemptionStatus(prize_data["redemption_status"]),
        redemption_code=prize_data.get("redemption_code"),
        redeemed_at=None,
        used_at=None,
        expired_at=prize_data.get("expired_at"),
        notes=None,
        created_at=prize_data["created_at"],
        updated_at=prize_data["created_at"],
        prize_name=prize_data["prize_name"],
        prize_type=prize_data["prize_type"],
        prize_image_url=prize_data.get("prize_image_url"),
        prize_value=prize_data.get("prize_value"),
        redemption_instructions=prize_data.get("redemption_instructions")
    )
    
    return OpenBlindBoxResponse(
        success=True,
        message=result["message"],
        data=prize_public
    )


@router.get("/blind-boxes/stats", response_model=BlindBoxStats)
def get_blind_box_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BlindBoxStats:
    """获取盲盒统计信息"""
    service = create_blindbox_service(db)
    stats = service.get_user_blind_box_stats(current_user.id)
    
    return BlindBoxStats(**stats)


# ==================== 奖品相关接口 ====================

@router.get("/prizes/my", response_model=BlindBoxUserPrizesPublic)
def get_my_prizes(
    redemption_status: Optional[PrizeRedemptionStatus] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BlindBoxUserPrizesPublic:
    """
    获取我的奖品列表
    
    - **redemption_status**: 兑换状态筛选（可选）
    """
    skip = (page - 1) * page_size
    
    prizes, total, unredeemed_count, redeemed_count = crud_blindbox.get_user_prizes(
        session=db,
        user_id=current_user.id,
        redemption_status=redemption_status,
        skip=skip,
        limit=page_size
    )
    
    # 组装响应数据
    prizes_data = []
    for prize in prizes:
        prize_dict = prize.model_dump()
        # 添加奖品模板信息
        if prize.prize_template:
            prize_dict["prize_name"] = prize.prize_template.name
            prize_dict["prize_type"] = prize.prize_template.prize_type.value
            prize_dict["prize_image_url"] = prize.prize_template.image_url
            prize_dict["prize_value"] = prize.prize_template.prize_value
            prize_dict["redemption_instructions"] = prize.prize_template.redemption_instructions
        
        prizes_data.append(BlindBoxUserPrizePublic(**prize_dict))
    
    return BlindBoxUserPrizesPublic(
        data=prizes_data,
        total=total,
        unredeemed_count=unredeemed_count,
        redeemed_count=redeemed_count
    )


@router.post("/prizes/{prize_id}/redeem")
def redeem_prize(
    prize_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    兑换奖品
    
    - **prize_id**: 奖品ID
    """
    # 获取奖品
    prize = crud_blindbox.get_user_prize(session=db, prize_id=prize_id)
    if not prize:
        raise HTTPException(status_code=404, detail="奖品不存在")
    
    # 检查所有权
    if prize.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权兑换此奖品")
    
    # 兑换奖品
    prize = crud_blindbox.redeem_user_prize(session=db, prize_id=prize_id)
    if not prize:
        raise HTTPException(status_code=400, detail="奖品已兑换或兑换失败")
    
    return {
        "success": True,
        "message": "兑换成功",
        "data": BlindBoxUserPrizePublic.model_validate(prize)
    }

