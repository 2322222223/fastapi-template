"""
弹窗配置CRUD操作
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func

from app.models import (
    DialogConfig, DialogConfigCreate, DialogConfigUpdate, DialogConfigPublic,
    DialogDisplayRecord, DialogDisplayRecordCreate, DialogDisplayRecordPublic,
    DialogTriggerEvent, DialogType, TargetAudience, DisplayFrequency, User
)


def create_dialog_config(
    *, session: Session, dialog_config: DialogConfigCreate
) -> DialogConfig:
    """创建弹窗配置"""
    db_obj = DialogConfig.model_validate(
        dialog_config, update={"id": uuid.uuid4()}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_dialog_config_by_id(
    *, session: Session, dialog_config_id: uuid.UUID
) -> Optional[DialogConfig]:
    """根据ID获取弹窗配置"""
    return session.get(DialogConfig, dialog_config_id)


def get_dialog_configs(
    *, session: Session, skip: int = 0, limit: int = 100,
    is_active: Optional[bool] = None, trigger_event: Optional[DialogTriggerEvent] = None
) -> Tuple[List[DialogConfig], int]:
    """获取弹窗配置列表"""
    # 构建查询条件
    conditions = []
    if is_active is not None:
        conditions.append(DialogConfig.is_active == is_active)
    if trigger_event is not None:
        conditions.append(DialogConfig.trigger_event == trigger_event)
    
    # 查询配置列表
    query = session.query(DialogConfig)
    if conditions:
        query = query.filter(and_(*conditions))
    query = query.order_by(DialogConfig.priority.desc(), DialogConfig.created_at.desc()).offset(skip).limit(limit)
    
    configs = query.all()
    
    # 查询总数
    count_query = session.query(func.count(DialogConfig.id))
    if conditions:
        count_query = count_query.filter(and_(*conditions))
    total = count_query.scalar() or 0
    
    return configs, total


def update_dialog_config(
    *, session: Session, dialog_config_id: uuid.UUID, 
    dialog_config_update: DialogConfigUpdate
) -> Optional[DialogConfig]:
    """更新弹窗配置"""
    dialog_config = session.get(DialogConfig, dialog_config_id)
    if not dialog_config:
        return None
    
    # 更新字段
    update_data = dialog_config_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dialog_config, field, value)
    
    dialog_config.updated_at = datetime.utcnow()
    session.add(dialog_config)
    session.commit()
    session.refresh(dialog_config)
    return dialog_config


def delete_dialog_config(
    *, session: Session, dialog_config_id: uuid.UUID
) -> bool:
    """删除弹窗配置"""
    dialog_config = session.get(DialogConfig, dialog_config_id)
    if not dialog_config:
        return False
    
    session.delete(dialog_config)
    session.commit()
    return True


def get_active_dialog_configs_for_event(
    *, session: Session, trigger_event: Union[DialogTriggerEvent, str], 
    user_id: Optional[uuid.UUID] = None
) -> List[DialogConfig]:
    """获取指定事件的有效弹窗配置"""
    now = datetime.utcnow()
    
    # 基础查询条件
    conditions = [
        DialogConfig.is_active == True,
        DialogConfig.trigger_event == trigger_event,
        DialogConfig.start_time <= now,
        DialogConfig.end_time >= now
    ]
    
    # 如果有用户ID，可以根据用户群体筛选
    if user_id:
        # 这里可以添加用户群体筛选逻辑
        # 暂时返回所有符合条件的配置
        pass
    
    # 使用session.query方式查询
    query = session.query(DialogConfig).filter(and_(*conditions)).order_by(
        DialogConfig.priority.desc(), DialogConfig.created_at.desc()
    )
    
    return query.all()


def create_dialog_display_record(
    *, session: Session, display_record: DialogDisplayRecordCreate
) -> DialogDisplayRecord:
    """创建弹窗显示记录"""
    # 检查是否已存在记录
    existing_record = session.exec(
        select(DialogDisplayRecord).where(
            and_(
                DialogDisplayRecord.user_id == display_record.user_id,
                DialogDisplayRecord.dialog_config_id == display_record.dialog_config_id
            )
        )
    ).first()
    
    if existing_record:
        # 更新现有记录
        existing_record.display_count += 1
        existing_record.last_displayed_at = datetime.utcnow()
        existing_record.updated_at = datetime.utcnow()
        session.add(existing_record)
        session.commit()
        session.refresh(existing_record)
        return existing_record
    else:
        # 创建新记录
        db_obj = DialogDisplayRecord.model_validate(
            display_record, update={"id": uuid.uuid4()}
        )
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj


def get_user_dialog_display_records(
    *, session: Session, user_id: uuid.UUID, 
    skip: int = 0, limit: int = 100
) -> Tuple[List[DialogDisplayRecord], int]:
    """获取用户的弹窗显示记录"""
    # 查询显示记录
    query = select(DialogDisplayRecord).where(
        DialogDisplayRecord.user_id == user_id
    ).order_by(DialogDisplayRecord.last_displayed_at.desc()).offset(skip).limit(limit)
    
    records = session.exec(query).all()
    
    # 查询总数
    count_query = select(func.count(DialogDisplayRecord.id)).where(
        DialogDisplayRecord.user_id == user_id
    )
    total = session.exec(count_query).scalar() or 0
    
    return list(records), total


def check_dialog_display_frequency(
    *, session: Session, user_id: uuid.UUID, dialog_config_id: uuid.UUID,
    display_frequency: DisplayFrequency
) -> bool:
    """检查弹窗显示频率是否符合要求"""
    now = datetime.utcnow()
    
    # 获取用户的显示记录
    record = session.exec(
        select(DialogDisplayRecord).where(
            and_(
                DialogDisplayRecord.user_id == user_id,
                DialogDisplayRecord.dialog_config_id == dialog_config_id
            )
        )
    ).first()
    
    if not record:
        return True  # 没有显示记录，可以显示
    
    # 根据显示频率检查
    if display_frequency == DisplayFrequency.ONCE:
        return False  # 只显示一次，已显示过
    elif display_frequency == DisplayFrequency.DAILY:
        # 检查是否今天已显示
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return record.last_displayed_at < today_start
    elif display_frequency == DisplayFrequency.WEEKLY:
        # 检查是否本周已显示
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        return record.last_displayed_at < week_start
    elif display_frequency == DisplayFrequency.ALWAYS:
        return True  # 总是显示
    
    return True


def get_dialog_configs_for_user(
    *, session: Session, user_id: uuid.UUID, trigger_event: Union[DialogTriggerEvent, str]
) -> List[DialogConfig]:
    """获取用户应该看到的弹窗配置"""
    # 获取所有有效的弹窗配置
    configs = get_active_dialog_configs_for_event(
        session=session, trigger_event=trigger_event, user_id=user_id
    )
    
    # 过滤掉不符合显示频率的配置
    filtered_configs = []
    for config in configs:
        if check_dialog_display_frequency(
            session=session, 
            user_id=user_id, 
            dialog_config_id=config.id,
            display_frequency=config.display_frequency
        ):
            filtered_configs.append(config)
    
    return filtered_configs
