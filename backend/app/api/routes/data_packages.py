from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.crud_data_package import (
    create_data_package,
    delete_data_package,
    get_active_data_packages,
    get_data_package,
    get_data_packages_by_user,
    get_data_packages_by_user_and_type,
    update_data_package,
    update_data_package_usage,
)
from app.models import DataPackage, DataPackageCreate, DataPackagePublic, DataPackageUpdate

router = APIRouter()


@router.get("/", response_model=List[DataPackagePublic])
def get_data_packages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    package_type: str = Query(None, description="包类型过滤：GENERAL, APP_SPECIFIC"),
    active_only: bool = Query(False, description="只返回有效流量包"),
) -> List[DataPackage]:
    """获取当前用户的流量包列表"""
    if active_only:
        data_packages = get_active_data_packages(session, current_user.id)
    elif package_type:
        data_packages = get_data_packages_by_user_and_type(session, current_user.id, package_type)
    else:
        data_packages = get_data_packages_by_user(session, current_user.id)
    
    return data_packages


@router.get("/{data_package_id}", response_model=DataPackagePublic)
def get_data_package_by_id(
    data_package_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> DataPackage:
    """获取指定流量包详情"""
    data_package = get_data_package(session, data_package_id)
    if not data_package:
        raise HTTPException(status_code=404, detail="流量包不存在")
    
    # 检查权限：只能查看自己的流量包
    if data_package.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此流量包")
    
    return data_package


@router.post("/", response_model=DataPackagePublic)
def create_new_data_package(
    data_package: DataPackageCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> DataPackage:
    """创建新的流量包"""
    # 设置用户ID为当前用户
    data_package.user_id = current_user.id
    return create_data_package(session, data_package)


@router.put("/{data_package_id}", response_model=DataPackagePublic)
def update_data_package_by_id(
    data_package_id: UUID,
    data_package_update: DataPackageUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> DataPackage:
    """更新流量包信息"""
    data_package = get_data_package(session, data_package_id)
    if not data_package:
        raise HTTPException(status_code=404, detail="流量包不存在")
    
    # 检查权限：只能更新自己的流量包
    if data_package.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此流量包")
    
    updated_data_package = update_data_package(session, data_package_id, data_package_update)
    if not updated_data_package:
        raise HTTPException(status_code=404, detail="流量包不存在")
    
    return updated_data_package


@router.put("/{data_package_id}/usage", response_model=DataPackagePublic)
def update_data_package_usage_by_id(
    data_package_id: UUID,
    *,
    used_mb: int = Query(..., description="已使用流量（MB）"),
    session: SessionDep,
    current_user: CurrentUser,
) -> DataPackage:
    """更新流量包使用量"""
    data_package = get_data_package(session, data_package_id)
    if not data_package:
        raise HTTPException(status_code=404, detail="流量包不存在")
    
    # 检查权限：只能更新自己的流量包
    if data_package.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此流量包")
    
    updated_data_package = update_data_package_usage(session, data_package_id, used_mb)
    if not updated_data_package:
        raise HTTPException(status_code=404, detail="流量包不存在")
    
    return updated_data_package


@router.delete("/{data_package_id}")
def delete_data_package_by_id(
    data_package_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """删除流量包"""
    data_package = get_data_package(session, data_package_id)
    if not data_package:
        raise HTTPException(status_code=404, detail="流量包不存在")
    
    # 检查权限：只能删除自己的流量包
    if data_package.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此流量包")
    
    success = delete_data_package(session, data_package_id)
    if not success:
        raise HTTPException(status_code=404, detail="流量包不存在")
    
    return {"message": "流量包删除成功"}


# 管理员接口
@router.get("/admin/all", response_model=List[DataPackagePublic], dependencies=[Depends(get_current_active_superuser)])
def get_all_data_packages(
    *,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> List[DataPackage]:
    """获取所有用户的流量包（管理员）"""
    from sqlmodel import select
    statement = select(DataPackage).offset(skip).limit(limit)
    return list(session.exec(statement).all())


@router.get("/admin/user/{user_id}", response_model=List[DataPackagePublic], dependencies=[Depends(get_current_active_superuser)])
def get_user_data_packages_admin(
    user_id: UUID,
    *,
    session: SessionDep,
) -> List[DataPackage]:
    """获取指定用户的所有流量包（管理员）"""
    return get_data_packages_by_user(session, user_id)
