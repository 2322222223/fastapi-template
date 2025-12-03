"""
地址管理CRUD操作
"""
from typing import Optional, List
from sqlmodel import Session, select, and_
from uuid import UUID
from datetime import datetime

from app.models import (
    Address, 
    AddressCreate, 
    AddressUpdate, 
    AddressPublic
)


def create_address(session: Session, user_id: UUID, address_data: AddressCreate) -> Address:
    """创建地址"""
    # 如果设置为默认地址，需要先取消其他默认地址
    if address_data.is_default:
        _clear_default_address(session, user_id)
    
    address = Address(**address_data.dict(), user_id=user_id)
    session.add(address)
    session.commit()
    session.refresh(address)
    return address


def get_address(session: Session, address_id: UUID, user_id: Optional[UUID] = None) -> Optional[Address]:
    """根据ID获取地址"""
    address = session.get(Address, address_id)
    if address and user_id and address.user_id != user_id:
        return None
    return address


def get_addresses(
    session: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100
) -> tuple[List[Address], int]:
    """获取用户地址列表"""
    query = select(Address).where(Address.user_id == user_id)
    query = query.order_by(Address.is_default.desc(), Address.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    addresses = session.exec(query).all()
    
    # 获取总数
    from sqlmodel import func
    count_query = select(func.count()).select_from(Address).where(Address.user_id == user_id)
    total = session.exec(count_query).one() or 0
    
    return addresses, total


def get_default_address(session: Session, user_id: UUID) -> Optional[Address]:
    """获取用户默认地址"""
    query = select(Address).where(
        and_(
            Address.user_id == user_id,
            Address.is_default == True
        )
    )
    return session.exec(query).first()


def update_address(
    session: Session, 
    address_id: UUID,
    user_id: UUID,
    address_data: AddressUpdate
) -> Optional[Address]:
    """更新地址"""
    address = session.get(Address, address_id)
    if not address:
        return None
    
    # 验证地址属于该用户
    if address.user_id != user_id:
        return None
    
    # 如果设置为默认地址，需要先取消其他默认地址
    update_data = address_data.dict(exclude_unset=True)
    if update_data.get("is_default") is True:
        _clear_default_address(session, user_id, exclude_address_id=address_id)
    
    # 更新字段
    for field, value in update_data.items():
        setattr(address, field, value)
    
    # 更新更新时间
    address.updated_at = datetime.utcnow()
    
    session.add(address)
    session.commit()
    session.refresh(address)
    return address


def delete_address(session: Session, address_id: UUID, user_id: UUID) -> bool:
    """删除地址"""
    address = session.get(Address, address_id)
    if not address:
        return False
    
    # 验证地址属于该用户
    if address.user_id != user_id:
        return False
    
    session.delete(address)
    session.commit()
    return True


def set_default_address(session: Session, address_id: UUID, user_id: UUID) -> Optional[Address]:
    """设置默认地址"""
    address = session.get(Address, address_id)
    if not address:
        return None
    
    # 验证地址属于该用户
    if address.user_id != user_id:
        return None
    
    # 取消其他默认地址
    _clear_default_address(session, user_id, exclude_address_id=address_id)
    
    # 设置当前地址为默认
    address.is_default = True
    address.updated_at = datetime.utcnow()
    
    session.add(address)
    session.commit()
    session.refresh(address)
    return address


def _clear_default_address(
    session: Session, 
    user_id: UUID, 
    exclude_address_id: Optional[UUID] = None
) -> None:
    """清除用户的其他默认地址"""
    conditions = [
        Address.user_id == user_id,
        Address.is_default == True
    ]
    
    if exclude_address_id:
        conditions.append(Address.id != exclude_address_id)
    
    query = select(Address).where(and_(*conditions))
    addresses = session.exec(query).all()
    
    for addr in addresses:
        addr.is_default = False
        addr.updated_at = datetime.utcnow()
        session.add(addr)
    
    session.commit()

