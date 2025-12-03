"""
弹窗配置API路由
"""
import uuid
from datetime import datetime
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user, get_current_active_superuser
from app.models import (
    User, DialogConfig, DialogConfigCreate, DialogConfigUpdate, DialogConfigPublic,
    DialogConfigsPublic, DialogTriggerEvent, DialogType, TargetAudience, DisplayFrequency,
    DialogDisplayRecordCreate
)
from app.crud_dialog import (
    create_dialog_config, get_dialog_config_by_id, get_dialog_configs,
    update_dialog_config, delete_dialog_config, get_dialog_configs_for_user,
    create_dialog_display_record
)

router = APIRouter()


# 响应模型定义
class DialogConfigData(BaseModel):
    id: str
    name: str
    priority: int
    trigger_event: str
    dialog_type: str
    payload: Optional[str] = None
    buttons: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_active: bool
    target_audience: str
    display_frequency: str
    max_display_count: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DialogConfigResponse(BaseModel):
    success: bool
    message: str
    data: Optional[DialogConfigData] = None


class DialogConfigsListResponse(BaseModel):
    success: bool
    data: DialogConfigsPublic


class DialogTriggerRequest(BaseModel):
    trigger_event: DialogTriggerEvent


class DialogTriggerResponse(BaseModel):
    success: bool
    data: List[DialogConfigData]


class DialogDisplayRequest(BaseModel):
    dialog_config_id: str


class DialogDisplayResponse(BaseModel):
    success: bool
    message: str


# 管理员接口
@router.post("/", response_model=DialogConfigResponse)
def create_dialog_config_endpoint(
    dialog_config: DialogConfigCreate,
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> DialogConfigResponse:
    """
    创建弹窗配置（管理员）
    
    注意：
    - payload 可以为空，此时弹窗将使用 name 和 description 字段来渲染内容
    - buttons 必须是有效的JSON数组字符串，包含按钮配置
    - 如果 payload 不为空，必须是有效的JSON字符串
    """
    try:
        # 验证JSON字段格式
        import json
        if dialog_config.payload and dialog_config.payload.strip():
            try:
                json.loads(dialog_config.payload)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"payload JSON格式错误: {str(e)}")
        
        if dialog_config.buttons and dialog_config.buttons.strip():
            try:
                json.loads(dialog_config.buttons)
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"buttons JSON格式错误: {str(e)}")
        
        config = create_dialog_config(session=db, dialog_config=dialog_config)
        
        return DialogConfigResponse(
            success=True,
            message="弹窗配置创建成功",
            data=DialogConfigData(
                id=str(config.id),
                name=config.name,
                priority=config.priority,
                trigger_event=config.trigger_event,
                dialog_type=config.dialog_type.value,
                payload=config.payload,
                buttons=config.buttons,
                start_time=config.start_time,
                end_time=config.end_time,
                is_active=config.is_active,
                target_audience=config.target_audience.value,
                display_frequency=config.display_frequency.value,
                max_display_count=config.max_display_count,
                description=config.description,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建失败：{str(e)}")


@router.get("/", response_model=DialogConfigsListResponse)
def get_dialog_configs_endpoint(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    is_active: Optional[bool] = Query(default=None, description="是否激活"),
    trigger_event: Optional[DialogTriggerEvent] = Query(default=None, description="触发事件"),
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> DialogConfigsListResponse:
    """
    获取弹窗配置列表（管理员）
    """
    skip = (page - 1) * page_size
    configs, total = get_dialog_configs(
        session=db,
        skip=skip,
        limit=page_size,
        is_active=is_active,
        trigger_event=trigger_event
    )
    
    # 格式化配置数据
    formatted_configs = []
    for config in configs:
        formatted_configs.append(DialogConfigPublic(
            id=config.id,
            name=config.name,
            priority=config.priority,
            trigger_event=config.trigger_event,
            dialog_type=config.dialog_type,
            payload=config.payload,
            buttons=config.buttons,
            start_time=config.start_time,
            end_time=config.end_time,
            is_active=config.is_active,
            target_audience=config.target_audience,
            display_frequency=config.display_frequency,
            max_display_count=config.max_display_count,
            description=config.description,
            created_at=config.created_at,
            updated_at=config.updated_at
        ))
    
    return DialogConfigsListResponse(
        success=True,
        data=DialogConfigsPublic(
            data=formatted_configs,
            count=total,
            is_more=(page * page_size) < total
        )
    )


@router.get("/{dialog_config_id}", response_model=DialogConfigResponse)
def get_dialog_config_endpoint(
    dialog_config_id: str,
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> DialogConfigResponse:
    """
    获取弹窗配置详情（管理员）
    """
    config = get_dialog_config_by_id(session=db, dialog_config_id=uuid.UUID(dialog_config_id))
    if not config:
        raise HTTPException(status_code=404, detail="弹窗配置不存在")
    
    return DialogConfigResponse(
        success=True,
        data=DialogConfigData(
            id=str(config.id),
            name=config.name,
            priority=config.priority,
            trigger_event=config.trigger_event,
            dialog_type=config.dialog_type.value,
            payload=config.payload,
            buttons=config.buttons,
            start_time=config.start_time,
            end_time=config.end_time,
            is_active=config.is_active,
            target_audience=config.target_audience.value,
            display_frequency=config.display_frequency.value,
            max_display_count=config.max_display_count,
            description=config.description,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
    )


@router.put("/{dialog_config_id}", response_model=DialogConfigResponse)
def update_dialog_config_endpoint(
    dialog_config_id: str,
    dialog_config_update: DialogConfigUpdate,
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> DialogConfigResponse:
    """
    更新弹窗配置（管理员）
    """
    # 验证JSON字段格式
    import json
    if dialog_config_update.payload and dialog_config_update.payload.strip():
        try:
            json.loads(dialog_config_update.payload)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"payload JSON格式错误: {str(e)}")
    
    if dialog_config_update.buttons and dialog_config_update.buttons.strip():
        try:
            json.loads(dialog_config_update.buttons)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"buttons JSON格式错误: {str(e)}")
    
    config = update_dialog_config(
        session=db,
        dialog_config_id=uuid.UUID(dialog_config_id),
        dialog_config_update=dialog_config_update
    )
    
    if not config:
        raise HTTPException(status_code=404, detail="弹窗配置不存在")
    
    return DialogConfigResponse(
        success=True,
        message="弹窗配置更新成功",
        data=DialogConfigData(
            id=str(config.id),
            name=config.name,
            priority=config.priority,
            trigger_event=config.trigger_event,
            dialog_type=config.dialog_type.value,
            payload=config.payload,
            buttons=config.buttons,
            start_time=config.start_time,
            end_time=config.end_time,
            is_active=config.is_active,
            target_audience=config.target_audience.value,
            display_frequency=config.display_frequency.value,
            max_display_count=config.max_display_count,
            description=config.description,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
    )


@router.delete("/{dialog_config_id}")
def delete_dialog_config_endpoint(
    dialog_config_id: str,
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
) -> dict:
    """
    删除弹窗配置（管理员）
    """
    success = delete_dialog_config(session=db, dialog_config_id=uuid.UUID(dialog_config_id))
    if not success:
        raise HTTPException(status_code=404, detail="弹窗配置不存在")
    
    return {"success": True, "message": "弹窗配置删除成功"}


# 用户接口
@router.get("/event/{event_name}", response_model=DialogConfigResponse)
def get_dialog_config_by_event(
    event_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DialogConfigResponse:
    """
    根据触发事件获取单个弹窗配置（用户）
    返回优先级最高的有效弹窗配置
    
    支持的事件类型：
    - 预定义事件：APP_LAUNCH, ENTER_STORE_PAGE, ENTER_PRODUCT_PAGE, USER_LOGIN, ORDER_COMPLETE
    - 自定义事件：任何字符串，如 MY_PAGE_LOAD, SPECIAL_EVENT 等
    """
    try:
        # 尝试解析为预定义事件，如果失败则作为自定义事件处理
        try:
            trigger_event = DialogTriggerEvent(event_name)
        except ValueError:
            # 作为自定义事件处理，直接使用字符串
            trigger_event = event_name
        
        # 获取用户应该看到的弹窗配置
        configs = get_dialog_configs_for_user(
            session=db, user_id=current_user.id, trigger_event=trigger_event
        )
        
        if not configs:
            return DialogConfigResponse(
                success=False,
                message="没有找到有效的弹窗配置",
                data=None
            )
        
        # 返回优先级最高的配置（已经按优先级排序）
        config = configs[0]
        
        return DialogConfigResponse(
            success=True,
            message="获取弹窗配置成功",
            data=DialogConfigData(
                id=str(config.id),
                name=config.name,
                priority=config.priority,
                trigger_event=config.trigger_event,  # 现在是字符串，不需要.value
                dialog_type=config.dialog_type.value,
                payload=config.payload,
                buttons=config.buttons,
                start_time=config.start_time,
                end_time=config.end_time,
                is_active=config.is_active,
                target_audience=config.target_audience.value,
                display_frequency=config.display_frequency.value,
                max_display_count=config.max_display_count,
                description=config.description,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取弹窗配置失败：{str(e)}")


@router.post("/trigger", response_model=DialogTriggerResponse)
def get_dialogs_for_trigger(
    trigger_request: DialogTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DialogTriggerResponse:
    """
    获取指定事件的弹窗配置（用户）
    """
    configs = get_dialog_configs_for_user(
        session=db,
        user_id=current_user.id,
        trigger_event=trigger_request.trigger_event
    )
    
    # 格式化配置数据
    formatted_configs = []
    for config in configs:
        formatted_configs.append(DialogConfigData(
            id=str(config.id),
            name=config.name,
            priority=config.priority,
            trigger_event=config.trigger_event,
            dialog_type=config.dialog_type.value,
            payload=config.payload,
            buttons=config.buttons,
            start_time=config.start_time,
            end_time=config.end_time,
            is_active=config.is_active,
            target_audience=config.target_audience.value,
            display_frequency=config.display_frequency.value,
            max_display_count=config.max_display_count,
            description=config.description,
            created_at=config.created_at,
            updated_at=config.updated_at
        ))
    
    return DialogTriggerResponse(
        success=True,
        data=formatted_configs
    )


@router.post("/display", response_model=DialogDisplayResponse)
def record_dialog_display(
    display_request: DialogDisplayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DialogDisplayResponse:
    """
    记录弹窗显示（用户）
    """
    try:
        display_record = DialogDisplayRecordCreate(
            user_id=current_user.id,
            dialog_config_id=uuid.UUID(display_request.dialog_config_id)
        )
        
        create_dialog_display_record(session=db, display_record=display_record)
        
        return DialogDisplayResponse(
            success=True,
            message="弹窗显示记录成功"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"记录失败：{str(e)}")


# 获取所有触发事件和弹窗类型
@router.get("/enums/trigger-events")
def get_trigger_events() -> dict:
    """获取所有触发事件"""
    return {
        "trigger_events": [event.value for event in DialogTriggerEvent],
        "dialog_types": [dialog_type.value for dialog_type in DialogType],
        "target_audiences": [audience.value for audience in TargetAudience],
        "display_frequencies": [frequency.value for frequency in DisplayFrequency]
    }
