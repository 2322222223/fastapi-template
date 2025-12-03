from typing import List, Optional
from uuid import UUID

from sqlmodel import Session, select

from app.models import DataPackage, DataPackageCreate, DataPackageUpdate


def create_data_package(session: Session, data_package: DataPackageCreate) -> DataPackage:
    """创建流量包"""
    db_data_package = DataPackage.model_validate(data_package)
    session.add(db_data_package)
    session.commit()
    session.refresh(db_data_package)
    return db_data_package


def get_data_package(session: Session, data_package_id: UUID) -> Optional[DataPackage]:
    """根据ID获取流量包"""
    statement = select(DataPackage).where(DataPackage.id == data_package_id)
    return session.exec(statement).first()


def get_data_packages_by_user(session: Session, user_id: UUID) -> List[DataPackage]:
    """获取用户的所有流量包"""
    statement = select(DataPackage).where(DataPackage.user_id == user_id)
    return list(session.exec(statement).all())


def get_data_packages_by_user_and_type(
    session: Session, user_id: UUID, package_type: str
) -> List[DataPackage]:
    """获取用户指定类型的流量包"""
    statement = select(DataPackage).where(
        DataPackage.user_id == user_id,
        DataPackage.package_type == package_type
    )
    return list(session.exec(statement).all())


def get_active_data_packages(session: Session, user_id: UUID) -> List[DataPackage]:
    """获取用户的有效流量包"""
    statement = select(DataPackage).where(
        DataPackage.user_id == user_id,
        DataPackage.status == "ACTIVE"
    )
    return list(session.exec(statement).all())


def update_data_package(
    session: Session, data_package_id: UUID, data_package_update: DataPackageUpdate
) -> Optional[DataPackage]:
    """更新流量包"""
    db_data_package = get_data_package(session, data_package_id)
    if not db_data_package:
        return None
    
    data = data_package_update.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(db_data_package, key, value)
    
    session.add(db_data_package)
    session.commit()
    session.refresh(db_data_package)
    return db_data_package


def delete_data_package(session: Session, data_package_id: UUID) -> bool:
    """删除流量包"""
    db_data_package = get_data_package(session, data_package_id)
    if not db_data_package:
        return False
    
    session.delete(db_data_package)
    session.commit()
    return True


def update_data_package_usage(
    session: Session, data_package_id: UUID, used_mb: int
) -> Optional[DataPackage]:
    """更新流量包使用量"""
    db_data_package = get_data_package(session, data_package_id)
    if not db_data_package:
        return None
    
    db_data_package.used_mb = used_mb
    
    # 检查是否已用尽
    if used_mb >= db_data_package.total_mb:
        db_data_package.status = "DEPLETED"
    
    session.add(db_data_package)
    session.commit()
    session.refresh(db_data_package)
    return db_data_package
