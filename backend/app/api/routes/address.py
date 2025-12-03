"""
地址管理API路由
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_db, get_current_user
from app.models import User, AddressCreate, AddressUpdate, AddressPublic, AddressListResponse
from app.crud_address import (
    create_address,
    get_address,
    get_addresses,
    get_default_address,
    update_address,
    delete_address,
    set_default_address
)

router = APIRouter()


@router.post("/", response_model=AddressPublic)
def create_address_endpoint(
    address_data: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建地址"""
    try:
        address = create_address(db, current_user.id, address_data)
        return address
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建地址失败：{str(e)}")


@router.get("/", response_model=AddressListResponse)
def get_addresses_endpoint(
    page: int = Query(0, ge=0, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的地址列表"""
    try:
        skip = page * page_size
        addresses, total = get_addresses(db, current_user.id, skip=skip, limit=page_size)
        
        return AddressListResponse(
            data=addresses,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取地址列表失败：{str(e)}")


@router.get("/default", response_model=AddressPublic)
def get_default_address_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取默认地址"""
    try:
        address = get_default_address(db, current_user.id)
        if not address:
            raise HTTPException(status_code=404, detail="未设置默认地址")
        return address
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取默认地址失败：{str(e)}")


@router.get("/{address_id}", response_model=AddressPublic)
def get_address_endpoint(
    address_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """根据ID获取地址"""
    try:
        address = get_address(db, address_id, current_user.id)
        if not address:
            raise HTTPException(status_code=404, detail="地址不存在或无权限访问")
        return address
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取地址失败：{str(e)}")


@router.put("/{address_id}", response_model=AddressPublic)
def update_address_endpoint(
    address_id: UUID,
    address_data: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新地址"""
    try:
        address = update_address(db, address_id, current_user.id, address_data)
        if not address:
            raise HTTPException(status_code=404, detail="地址不存在或无权限访问")
        return address
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新地址失败：{str(e)}")


@router.delete("/{address_id}")
def delete_address_endpoint(
    address_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除地址"""
    try:
        success = delete_address(db, address_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="地址不存在或无权限访问")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"删除地址失败：{str(e)}")


@router.put("/{address_id}/set-default", response_model=AddressPublic)
def set_default_address_endpoint(
    address_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """设置默认地址"""
    try:
        address = set_default_address(db, address_id, current_user.id)
        if not address:
            raise HTTPException(status_code=404, detail="地址不存在或无权限访问")
        return address
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"设置默认地址失败：{str(e)}")

