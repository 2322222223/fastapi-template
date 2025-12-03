"""
服务号CRUD操作
"""
from typing import Optional, List
from sqlmodel import Session, select, func, and_
from uuid import UUID

from app.models import (
    ServiceAccount, 
    ServiceAccountCreate, 
    ServiceAccountUpdate, 
    ServiceAccountPublic,
    ServiceAccountType
)


def create_service_account(session: Session, service_account_data: ServiceAccountCreate) -> ServiceAccount:
    """创建服务号"""
    service_account = ServiceAccount(**service_account_data.dict())
    session.add(service_account)
    session.commit()
    session.refresh(service_account)
    return service_account


def get_service_account(session: Session, service_account_id: UUID) -> Optional[ServiceAccount]:
    """根据ID获取服务号"""
    return session.get(ServiceAccount, service_account_id)


def get_service_accounts(
    session: Session,
    account_type: Optional[ServiceAccountType] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[ServiceAccount], int]:
    """获取服务号列表"""
    # 构建查询条件
    conditions = []
    if account_type is not None:
        conditions.append(ServiceAccount.account_type == account_type)
    if is_active is not None:
        conditions.append(ServiceAccount.is_active == is_active)
    
    # 构建查询
    query = select(ServiceAccount)
    if conditions:
        query = query.where(and_(*conditions))
    
    # 排序
    query = query.order_by(ServiceAccount.created_at.desc())
    
    # 分页
    query = query.offset(skip).limit(limit)
    
    # 执行查询
    service_accounts = session.exec(query).all()
    
    # 获取总数
    count_query = select(func.count()).select_from(ServiceAccount)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = session.exec(count_query).one() or 0
    
    return service_accounts, total


def get_service_accounts_with_user_info(
    session: Session,
    account_type: Optional[ServiceAccountType] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[dict], int]:
    """获取服务号列表（包含用户信息）"""
    from app.models import User
    
    # 构建查询条件
    conditions = []
    if account_type is not None:
        conditions.append(ServiceAccount.account_type == account_type)
    if is_active is not None:
        conditions.append(ServiceAccount.is_active == is_active)
    
    # 构建查询
    query = select(ServiceAccount, User).join(User, ServiceAccount.user_id == User.id)
    if conditions:
        query = query.where(and_(*conditions))
    
    # 排序
    query = query.order_by(ServiceAccount.created_at.desc())
    
    # 分页
    query = query.offset(skip).limit(limit)
    
    # 执行查询
    results = session.exec(query).all()
    
    # 转换为字典格式
    service_accounts = []
    for service_account, user in results:
        account_dict = {
            "id": service_account.id,
            "user_id": service_account.user_id,
            "name": service_account.name,
            "avatar_url": service_account.avatar_url,
            "account_type": service_account.account_type,
            "description": service_account.description,
            "is_active": service_account.is_active,
            "created_at": service_account.created_at,
            "updated_at": service_account.updated_at,
            "user_name": user.full_name
        }
        service_accounts.append(account_dict)
    
    # 获取总数
    count_query = select(func.count()).select_from(ServiceAccount)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = session.exec(count_query).one() or 0
    
    return service_accounts, total


def update_service_account(
    session: Session, 
    service_account_id: UUID, 
    service_account_data: ServiceAccountUpdate
) -> Optional[ServiceAccount]:
    """更新服务号"""
    service_account = session.get(ServiceAccount, service_account_id)
    if not service_account:
        return None
    
    # 更新字段
    update_data = service_account_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service_account, field, value)
    
    # 更新更新时间
    from datetime import datetime
    service_account.updated_at = datetime.utcnow()
    
    session.add(service_account)
    session.commit()
    session.refresh(service_account)
    return service_account


def delete_service_account(session: Session, service_account_id: UUID) -> bool:
    """删除服务号"""
    service_account = session.get(ServiceAccount, service_account_id)
    if not service_account:
        return False
    
    session.delete(service_account)
    session.commit()
    return True


def get_service_account_by_type(
    session: Session, 
    account_type: ServiceAccountType
) -> List[ServiceAccount]:
    """根据类型获取服务号列表"""
    query = select(ServiceAccount).where(
        and_(
            ServiceAccount.account_type == account_type,
            ServiceAccount.is_active == True
        )
    ).order_by(ServiceAccount.created_at.desc())
    
    return session.exec(query).all()


def search_service_accounts(
    session: Session,
    keyword: str,
    account_type: Optional[ServiceAccountType] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[ServiceAccount], int]:
    """搜索服务号"""
    # 构建查询条件
    conditions = [
        ServiceAccount.is_active == True,
        ServiceAccount.name.ilike(f"%{keyword}%")
    ]
    
    if account_type is not None:
        conditions.append(ServiceAccount.account_type == account_type)
    
    # 构建查询
    query = select(ServiceAccount).where(and_(*conditions))
    query = query.order_by(ServiceAccount.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    # 执行查询
    service_accounts = session.exec(query).all()
    
    # 获取总数
    count_query = select(func.count()).select_from(ServiceAccount).where(and_(*conditions))
    total = session.exec(count_query).one() or 0
    
    return service_accounts, total
