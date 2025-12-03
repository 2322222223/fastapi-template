"""
服务号API路由
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_db, get_current_user
from app.models import User, ServiceAccountType
from app.crud_service_account import (
    create_service_account,
    get_service_account,
    get_service_accounts,
    get_service_accounts_with_user_info,
    update_service_account,
    delete_service_account,
    get_service_account_by_type,
    search_service_accounts
)
from app.models import (
    ServiceAccountCreate,
    ServiceAccountUpdate,
    ServiceAccountPublic,
    ServiceAccountListResponse
)

router = APIRouter()


@router.post("/", response_model=ServiceAccountPublic)
def create_service_account_endpoint(
    service_account_data: ServiceAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建服务号"""
    try:
        service_account = create_service_account(db, service_account_data)
        return service_account
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建服务号失败：{str(e)}")


@router.get("/", response_model=ServiceAccountListResponse)
def get_service_accounts_endpoint(
    account_type: Optional[ServiceAccountType] = Query(None, description="账号类型"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    page: int = Query(0, ge=0, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取服务号列表"""
    try:
        skip = page * page_size
        service_accounts, total = get_service_accounts_with_user_info(
            db, 
            account_type=account_type,
            is_active=is_active,
            skip=skip,
            limit=page_size
        )
        
        return ServiceAccountListResponse(
            data=service_accounts,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取服务号列表失败：{str(e)}")


@router.get("/{service_account_id}", response_model=ServiceAccountPublic)
def get_service_account_endpoint(
    service_account_id: UUID,
    db: Session = Depends(get_db)
):
    """根据ID获取服务号"""
    try:
        service_account = get_service_account(db, service_account_id)
        if not service_account:
            raise HTTPException(status_code=404, detail="服务号不存在")
        return service_account
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取服务号失败：{str(e)}")


@router.put("/{service_account_id}", response_model=ServiceAccountPublic)
def update_service_account_endpoint(
    service_account_id: UUID,
    service_account_data: ServiceAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新服务号"""
    try:
        service_account = update_service_account(db, service_account_id, service_account_data)
        if not service_account:
            raise HTTPException(status_code=404, detail="服务号不存在")
        return service_account
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新服务号失败：{str(e)}")


@router.delete("/{service_account_id}")
def delete_service_account_endpoint(
    service_account_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除服务号"""
    try:
        success = delete_service_account(db, service_account_id)
        if not success:
            raise HTTPException(status_code=404, detail="服务号不存在")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"删除服务号失败：{str(e)}")


@router.get("/type/{account_type}", response_model=ServiceAccountListResponse)
def get_service_accounts_by_type_endpoint(
    account_type: ServiceAccountType,
    page: int = Query(0, ge=0, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """根据类型获取服务号列表"""
    try:
        service_accounts = get_service_account_by_type(db, account_type)
        
        # 手动分页
        total = len(service_accounts)
        skip = page * page_size
        paginated_accounts = service_accounts[skip:skip + page_size]
        
        return ServiceAccountListResponse(
            data=paginated_accounts,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取服务号列表失败：{str(e)}")


@router.get("/search/", response_model=ServiceAccountListResponse)
def search_service_accounts_endpoint(
    keyword: str = Query(..., description="搜索关键词"),
    account_type: Optional[ServiceAccountType] = Query(None, description="账号类型"),
    page: int = Query(0, ge=0, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """搜索服务号"""
    try:
        skip = page * page_size
        service_accounts, total = search_service_accounts(
            db,
            keyword=keyword,
            account_type=account_type,
            skip=skip,
            limit=page_size
        )
        
        return ServiceAccountListResponse(
            data=service_accounts,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索服务号失败：{str(e)}")


@router.get("/enums/account-types")
def get_account_types():
    """获取账号类型枚举值"""
    return {
        "account_types": [
            {"value": account_type.value, "label": account_type.value}
            for account_type in ServiceAccountType
        ]
    }
