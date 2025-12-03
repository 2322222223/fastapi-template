"""
热搜相关的API路由
"""
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_current_user, CurrentUser, SessionDep
from app.models import (
    HotSearch, 
    HotSearchCreate, 
    HotSearchUpdate, 
    HotSearchPublic, 
    HotSearchesPublic,
    User
)
from app.crud_hot_search import (
    create, get, get_multi, update, delete, search_keywords, 
    get_total_count, get_by_keyword, create_if_not_exists,
    bulk_create, get_random, get_latest, exists
)

router = APIRouter()


@router.get("/list", response_model=HotSearchesPublic)
def read_hot_searches(
    session: SessionDep,
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量")
) -> Any:
    """
    获取热搜列表
    支持分页
    """
    # 获取热搜数据
    hot_searches = get_multi(session=session, skip=skip, limit=limit)
    
    # 获取总数
    total_count = get_total_count(session=session)
    
    # 计算是否有更多数据
    is_more = skip + limit < total_count
    
    return HotSearchesPublic(
        data=hot_searches,
        count=total_count,
        is_more=is_more
    )


@router.get("/random", response_model=List[HotSearchPublic])
def read_random_hot_searches(
    session: SessionDep,
    limit: int = Query(10, ge=1, le=50, description="返回数量")
) -> Any:
    """
    获取随机热搜
    """
    return get_random(session=session, limit=limit)


@router.get("/latest", response_model=List[HotSearchPublic])
def read_latest_hot_searches(
    session: SessionDep,
    limit: int = Query(10, ge=1, le=50, description="返回数量")
) -> Any:
    """
    获取最新热搜
    """
    return get_latest(session=session, limit=limit)


@router.get("/search", response_model=HotSearchesPublic)
def search_hot_searches(
    session: SessionDep,
    keyword: str = Query(..., description="搜索关键词"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量")
) -> Any:
    """
    搜索热搜关键词
    """
    hot_searches = search_keywords(
        session=session,
        keyword=keyword,
        skip=skip,
        limit=limit
    )
    
    # 简化处理，实际应该有专门的count搜索方法
    total_count = len(hot_searches) if len(hot_searches) < limit else len(hot_searches) + 1
    is_more = len(hot_searches) == limit
    
    return HotSearchesPublic(
        data=hot_searches,
        count=total_count,
        is_more=is_more
    )


@router.get("/{hot_search_id}", response_model=HotSearchPublic)
def read_hot_search(
    session: SessionDep,
    hot_search_id: UUID
) -> Any:
    """
    根据ID获取热搜详情
    """
    hot_search_obj = get(session=session, id=hot_search_id)
    if not hot_search_obj:
        raise HTTPException(status_code=404, detail="热搜不存在")
    return hot_search_obj


@router.get("/keyword/{keyword}", response_model=HotSearchPublic)
def read_hot_search_by_keyword(
    session: SessionDep,
    keyword: str
) -> Any:
    """
    根据关键词获取热搜
    """
    hot_search_obj = get_by_keyword(session=session, keyword=keyword)
    if not hot_search_obj:
        raise HTTPException(status_code=404, detail="热搜不存在")
    return hot_search_obj


@router.post("/", response_model=HotSearchPublic)
def create_hot_search(
    *,
    session: SessionDep,
    hot_search_in: HotSearchCreate,
    current_user: CurrentUser
) -> Any:
    """
    创建热搜（需要管理员权限）
    """
    # 检查权限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 检查是否已存在
    if exists(session, hot_search_in.keyword):
        raise HTTPException(status_code=400, detail="热搜关键词已存在")
    
    return create(session=session, obj_in=hot_search_in)


@router.post("/bulk", response_model=List[HotSearchPublic])
def create_bulk_hot_searches(
    *,
    session: SessionDep,
    hot_searches_in: List[HotSearchCreate],
    current_user: CurrentUser
) -> Any:
    """
    批量创建热搜（需要管理员权限）
    """
    # 检查权限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    return bulk_create(session=session, objs_in=hot_searches_in)


@router.post("/smart", response_model=HotSearchPublic)
def create_smart_hot_search(
    *,
    session: SessionDep,
    hot_search_in: HotSearchCreate,
    current_user: CurrentUser
) -> Any:
    """
    智能创建热搜（如果存在则返回现有的，不存在则创建新的）
    """
    # 检查权限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    return create_if_not_exists(session=session, obj_in=hot_search_in)


@router.put("/{hot_search_id}", response_model=HotSearchPublic)
def update_hot_search(
    *,
    session: SessionDep,
    hot_search_id: UUID,
    hot_search_in: HotSearchUpdate,
    current_user: CurrentUser
) -> Any:
    """
    更新热搜（需要管理员权限）
    """
    # 检查权限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    hot_search_obj = get(session=session, id=hot_search_id)
    if not hot_search_obj:
        raise HTTPException(status_code=404, detail="热搜不存在")
    
    # 如果要更新关键词，检查是否与其他热搜重复
    if hot_search_in.keyword and hot_search_in.keyword != hot_search_obj.keyword:
        if exists(session, hot_search_in.keyword):
            raise HTTPException(status_code=400, detail="热搜关键词已存在")
    
    return update(session=session, db_obj=hot_search_obj, obj_in=hot_search_in)


@router.delete("/{hot_search_id}")
def delete_hot_search(
    *,
    session: SessionDep,
    hot_search_id: UUID,
    current_user: CurrentUser
) -> Any:
    """
    删除热搜（需要管理员权限）
    """
    # 检查权限
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    success = delete(session=session, id=hot_search_id)
    if not success:
        raise HTTPException(status_code=404, detail="热搜不存在")
    
    return {"message": "热搜删除成功"}


@router.get("/check/{keyword}")
def check_keyword_exists(
    session: SessionDep,
    keyword: str
) -> Any:
    """
    检查关键词是否存在
    """
    exists_flag = exists(session, keyword)
    return {
        "keyword": keyword,
        "exists": exists_flag,
        "message": "关键词已存在" if exists_flag else "关键词可用"
    }


@router.get("/stats/count")
def get_hot_search_stats(
    session: SessionDep
) -> Any:
    """
    获取热搜统计信息
    """
    total_count = get_total_count(session=session)
    
    return {
        "total_count": total_count,
        "message": f"当前共有 {total_count} 个热搜"
    }