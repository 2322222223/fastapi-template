"""
发现页面API路由
"""
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models import (
    User, Article, CommunityTask, TaskApplication, Comment, Like,
    ArticleCreate, ArticleUpdate, ArticlePublic, ArticlesPublic,
    CommunityTaskCreate, CommunityTaskUpdate, CommunityTaskPublic, CommunityTasksPublic,
    TaskApplicationCreate, TaskApplicationUpdate, TaskApplicationPublic, TaskApplicationsPublic,
    CommentCreate, CommentPublic, CommentsPublic,
    LikePublic, LikesPublic,
    ArticleType, ArticleStatus, CommunityTaskType, CommunityTaskStatus, ApplicationStatus
)
from app.crud_discovery import (
    # 文章相关
    create_article, get_article, get_articles, update_article, delete_article,
    increment_article_view_count, update_article_hot_score,
    # 社区任务相关
    create_community_task, get_community_task, get_community_tasks, update_community_task, delete_community_task,
    # 任务申请相关
    create_task_application, get_task_application, get_task_applications, update_task_application,
    accept_task_application, reject_task_application,
    # 评论相关
    create_comment, get_comment, get_comments, delete_comment,
    # 点赞相关
    create_like, delete_like, get_like, get_likes,
    # 热度计算
    calculate_article_hot_score, update_all_article_hot_scores
)

router = APIRouter()


# ==================== 文章相关接口 ====================

@router.post("/articles", response_model=ArticlePublic)
def create_article_endpoint(
    article: ArticleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建文章"""
    try:
        db_article = create_article(session=db, article=article, user_id=current_user.id)
        return ArticlePublic.model_validate(db_article)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建文章失败: {str(e)}")


@router.get("/articles/{article_id}", response_model=ArticlePublic)
def get_article_endpoint(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文章详情"""
    article = get_article(session=db, article_id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 增加浏览数
    increment_article_view_count(session=db, article=article)
    
    # 获取作者信息
    author = db.get(User, article.user_id)
    author_name = author.full_name if author else None
    author_avatar_url = author.avatar_url if author else None
    
    article_public = ArticlePublic(
        id=article.id,
        user_id=article.user_id,
        title=article.title,
        content=article.content,
        cover_image_url=article.cover_image_url,
        type=article.type,
        status=article.status,
        view_count=article.view_count,
        like_count=article.like_count,
        comment_count=article.comment_count,
        share_count=article.share_count,
        hot_score=article.hot_score,
        created_at=article.created_at,
        updated_at=article.updated_at,
        author_name=author_name,
        author_avatar_url=author_avatar_url
    )
    
    return article_public


@router.get("/articles", response_model=ArticlesPublic)
def get_articles_endpoint(
    article_type: Optional[ArticleType] = Query(None, description="文章类型过滤"),
    status: Optional[ArticleStatus] = Query(None, description="文章状态过滤"),
    user_id: Optional[uuid.UUID] = Query(None, description="作者ID过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("hot_score", description="排序方式: hot_score, created_at, view_count"),
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文章列表"""
    skip = page * limit
    articles, total = get_articles(
        session=db,
        skip=skip,
        limit=limit,
        article_type=article_type,
        status=status,
        user_id=user_id,
        search=search,
        sort_by=sort_by
    )
    
    is_more = (skip + limit) < total
    
    return ArticlesPublic(
        data=articles,
        count=total,
        is_more=is_more
    )


@router.put("/articles/{article_id}", response_model=ArticlePublic)
def update_article_endpoint(
    article_id: uuid.UUID,
    article_update: ArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新文章"""
    article = get_article(session=db, article_id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 检查权限
    if article.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        updated_article = update_article(session=db, article=article, article_update=article_update)
        return ArticlePublic.model_validate(updated_article)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新文章失败: {str(e)}")


@router.delete("/articles/{article_id}")
def delete_article_endpoint(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除文章"""
    article = get_article(session=db, article_id=article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    # 检查权限
    if article.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        delete_article(session=db, article=article)
        return {"message": "文章删除成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"删除文章失败: {str(e)}")


# ==================== 社区任务相关接口 ====================

@router.post("/tasks", response_model=CommunityTaskPublic)
def create_community_task_endpoint(
    task: CommunityTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建社区任务"""
    try:
        db_task = create_community_task(session=db, task=task, user_id=current_user.id)
        return CommunityTaskPublic.model_validate(db_task)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建任务失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=CommunityTaskPublic)
def get_community_task_endpoint(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取社区任务详情"""
    task = get_community_task(session=db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取发布者信息
    publisher = db.get(User, task.user_id)
    publisher_name = publisher.full_name if publisher else None
    publisher_avatar_url = publisher.avatar_url if publisher else None
    
    # 获取申请数量
    from sqlmodel import select, func
    application_count = db.exec(
        select(func.count()).select_from(TaskApplication).where(
            TaskApplication.task_id == task.id
        )
    ).one() or 0
    
    task_public = CommunityTaskPublic(
        id=task.id,
        user_id=task.user_id,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        status=task.status,
        reward_info=task.reward_info,
        contact_info=task.contact_info,
        expiry_at=task.expiry_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        publisher_name=publisher_name,
        publisher_avatar_url=publisher_avatar_url,
        application_count=application_count
    )
    
    return task_public


@router.get("/tasks", response_model=CommunityTasksPublic)
def get_community_tasks_endpoint(
    task_type: Optional[CommunityTaskType] = Query(None, description="任务类型过滤"),
    status: Optional[CommunityTaskStatus] = Query(None, description="任务状态过滤"),
    user_id: Optional[uuid.UUID] = Query(None, description="发布者ID过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("created_at", description="排序方式: created_at, expiry_at"),
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取社区任务列表"""
    skip = page * limit
    tasks, total = get_community_tasks(
        session=db,
        skip=skip,
        limit=limit,
        task_type=task_type,
        status=status,
        user_id=user_id,
        search=search,
        sort_by=sort_by
    )
    
    is_more = (skip + limit) < total
    
    return CommunityTasksPublic(
        data=tasks,
        count=total,
        is_more=is_more
    )


@router.put("/tasks/{task_id}", response_model=CommunityTaskPublic)
def update_community_task_endpoint(
    task_id: uuid.UUID,
    task_update: CommunityTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新社区任务"""
    task = get_community_task(session=db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查权限
    if task.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        updated_task = update_community_task(session=db, task=task, task_update=task_update)
        return CommunityTaskPublic.model_validate(updated_task)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新任务失败: {str(e)}")


@router.delete("/tasks/{task_id}")
def delete_community_task_endpoint(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除社区任务"""
    task = get_community_task(session=db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查权限
    if task.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        delete_community_task(session=db, task=task)
        return {"message": "任务删除成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"删除任务失败: {str(e)}")


# ==================== 任务申请相关接口 ====================

@router.post("/task-applications", response_model=TaskApplicationPublic)
def create_task_application_endpoint(
    application: TaskApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """申请任务"""
    try:
        db_application = create_task_application(session=db, application=application, user_id=current_user.id)
        return TaskApplicationPublic.model_validate(db_application)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"申请任务失败: {str(e)}")


@router.get("/task-applications", response_model=TaskApplicationsPublic)
def get_task_applications_endpoint(
    task_id: Optional[uuid.UUID] = Query(None, description="任务ID过滤"),
    applicant_id: Optional[uuid.UUID] = Query(None, description="申请人ID过滤"),
    status: Optional[ApplicationStatus] = Query(None, description="申请状态过滤"),
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务申请列表"""
    skip = page * limit
    applications, total = get_task_applications(
        session=db,
        task_id=task_id,
        applicant_id=applicant_id,
        status=status,
        skip=skip,
        limit=limit
    )
    
    is_more = (skip + limit) < total
    
    return TaskApplicationsPublic(
        data=applications,
        count=total,
        is_more=is_more
    )


@router.put("/task-applications/{application_id}/accept")
def accept_task_application_endpoint(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """接受任务申请"""
    application = get_task_application(session=db, application_id=application_id)
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")
    
    # 检查权限（只有任务发布者可以接受申请）
    task = get_community_task(session=db, task_id=application.task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        accept_task_application(session=db, application=application)
        return {"message": "申请已接受"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"接受申请失败: {str(e)}")


@router.put("/task-applications/{application_id}/reject")
def reject_task_application_endpoint(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """拒绝任务申请"""
    application = get_task_application(session=db, application_id=application_id)
    if not application:
        raise HTTPException(status_code=404, detail="申请不存在")
    
    # 检查权限（只有任务发布者可以拒绝申请）
    task = get_community_task(session=db, task_id=application.task_id)
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        reject_task_application(session=db, application=application)
        return {"message": "申请已拒绝"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"拒绝申请失败: {str(e)}")


# ==================== 评论相关接口 ====================

@router.post("/comments", response_model=CommentPublic)
def create_comment_endpoint(
    comment: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建评论"""
    try:
        db_comment = create_comment(session=db, comment=comment, user_id=current_user.id)
        return CommentPublic.model_validate(db_comment)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建评论失败: {str(e)}")


@router.get("/comments", response_model=CommentsPublic)
def get_comments_endpoint(
    article_id: uuid.UUID = Query(..., description="文章ID"),
    parent_id: Optional[uuid.UUID] = Query(None, description="父评论ID，不传则获取顶级评论"),
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取评论列表"""
    skip = page * limit
    comments, total = get_comments(
        session=db,
        article_id=article_id,
        parent_id=parent_id,
        skip=skip,
        limit=limit
    )
    
    is_more = (skip + limit) < total
    
    return CommentsPublic(
        data=comments,
        count=total,
        is_more=is_more
    )


@router.delete("/comments/{comment_id}")
def delete_comment_endpoint(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除评论"""
    comment = get_comment(session=db, comment_id=comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    
    # 检查权限
    if comment.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        delete_comment(session=db, comment=comment)
        return {"message": "评论删除成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"删除评论失败: {str(e)}")


# ==================== 点赞相关接口 ====================

@router.post("/likes")
def create_like_endpoint(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """点赞文章"""
    try:
        create_like(session=db, user_id=current_user.id, article_id=article_id)
        return {"message": "点赞成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"点赞失败: {str(e)}")


@router.delete("/likes")
def delete_like_endpoint(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消点赞"""
    try:
        delete_like(session=db, user_id=current_user.id, article_id=article_id)
        return {"message": "取消点赞成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"取消点赞失败: {str(e)}")


@router.get("/likes", response_model=LikesPublic)
def get_likes_endpoint(
    article_id: Optional[uuid.UUID] = Query(None, description="文章ID过滤"),
    user_id: Optional[uuid.UUID] = Query(None, description="用户ID过滤"),
    page: int = Query(0, ge=0, description="页码，从0开始"),
    limit: int = Query(20, ge=1, le=100, description="每页数量，范围1-100"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取点赞列表"""
    skip = page * limit
    likes, total = get_likes(
        session=db,
        article_id=article_id,
        user_id=user_id,
        skip=skip,
        limit=limit
    )
    
    is_more = (skip + limit) < total
    
    return LikesPublic(
        data=likes,
        count=total,
        is_more=is_more
    )


@router.get("/likes/check")
def check_like_endpoint(
    article_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查是否已点赞"""
    like = get_like(session=db, user_id=current_user.id, article_id=article_id)
    return {"is_liked": like is not None}


# ==================== 管理接口 ====================

@router.post("/admin/update-hot-scores")
def update_hot_scores_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新所有文章热度分（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        updated_count = update_all_article_hot_scores(session=db)
        return {"message": f"成功更新 {updated_count} 篇文章的热度分"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新热度分失败: {str(e)}")


# ==================== 枚举值接口 ====================

@router.get("/enums/article-types")
def get_article_types():
    """获取文章类型枚举值"""
    return [{"value": item.value, "label": item.value} for item in ArticleType]


@router.get("/enums/article-statuses")
def get_article_statuses():
    """获取文章状态枚举值"""
    return [{"value": item.value, "label": item.value} for item in ArticleStatus]


@router.get("/enums/task-types")
def get_task_types():
    """获取任务类型枚举值"""
    return [{"value": item.value, "label": item.value} for item in CommunityTaskType]


@router.get("/enums/task-statuses")
def get_task_statuses():
    """获取任务状态枚举值"""
    return [{"value": item.value, "label": item.value} for item in CommunityTaskStatus]


@router.get("/enums/application-statuses")
def get_application_statuses():
    """获取申请状态枚举值"""
    return [{"value": item.value, "label": item.value} for item in ApplicationStatus]
