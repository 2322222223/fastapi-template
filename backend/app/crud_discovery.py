"""
发现页面CRUD操作
"""
import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import and_, or_, desc, func, text
from sqlalchemy.orm import Session
from sqlmodel import select

from app.models import (
    Article, ArticleCreate, ArticleUpdate, ArticlePublic,
    CommunityTask, CommunityTaskCreate, CommunityTaskUpdate, CommunityTaskPublic,
    TaskApplication, TaskApplicationCreate, TaskApplicationUpdate, TaskApplicationPublic,
    Comment, CommentCreate, CommentPublic,
    Like, LikePublic,
    User, ArticleType, ArticleStatus, CommunityTaskType, CommunityTaskStatus, ApplicationStatus
)


# ==================== 文章相关操作 ====================

def create_article(*, session: Session, article: ArticleCreate, user_id: uuid.UUID) -> Article:
    """创建文章"""
    db_article = Article.model_validate(
        article, update={"id": uuid.uuid4(), "user_id": user_id}
    )
    session.add(db_article)
    session.commit()
    session.refresh(db_article)
    return db_article


def get_article(*, session: Session, article_id: uuid.UUID) -> Optional[Article]:
    """根据ID获取文章"""
    return session.get(Article, article_id)


def get_articles(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 20,
    article_type: Optional[ArticleType] = None,
    status: Optional[ArticleStatus] = None,
    user_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    sort_by: str = "hot_score"  # hot_score, created_at, view_count
) -> Tuple[List[ArticlePublic], int]:
    """获取文章列表"""
    query = select(Article)
    
    # 过滤条件
    conditions = []
    if article_type:
        conditions.append(Article.type == article_type)
    if status:
        conditions.append(Article.status == status)
    else:
        # 默认只显示已发布的文章
        conditions.append(Article.status == ArticleStatus.PUBLISHED)
    if user_id:
        conditions.append(Article.user_id == user_id)
    if search:
        conditions.append(
            or_(
                Article.title.contains(search),
                Article.content.contains(search)
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # 排序
    if sort_by == "hot_score":
        query = query.order_by(desc(Article.hot_score), desc(Article.created_at))
    elif sort_by == "created_at":
        query = query.order_by(desc(Article.created_at))
    elif sort_by == "view_count":
        query = query.order_by(desc(Article.view_count), desc(Article.created_at))
    
    # 分页
    query = query.offset(skip).limit(limit)
    
    # 执行查询
    articles = session.exec(query).all()
    
    # 获取总数
    count_query = select(func.count()).select_from(Article)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = session.exec(count_query).one() or 0
    
    # 转换为公开模型
    article_publics = []
    for article in articles:
        # 获取作者信息
        author = session.get(User, article.user_id)
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
        article_publics.append(article_public)
    
    return article_publics, total


def update_article(*, session: Session, article: Article, article_update: ArticleUpdate) -> Article:
    """更新文章"""
    obj_data = article_update.model_dump(exclude_unset=True)
    article.sqlmodel_update(obj_data)
    article.updated_at = datetime.utcnow()
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


def delete_article(*, session: Session, article: Article) -> Article:
    """删除文章（软删除）"""
    article.status = ArticleStatus.DELETED
    article.updated_at = datetime.utcnow()
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


def increment_article_view_count(*, session: Session, article: Article) -> Article:
    """增加文章浏览数"""
    article.view_count += 1
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


def update_article_hot_score(*, session: Session, article: Article, hot_score: float) -> Article:
    """更新文章热度分"""
    article.hot_score = hot_score
    session.add(article)
    session.commit()
    session.refresh(article)
    return article


# ==================== 社区任务相关操作 ====================

def create_community_task(*, session: Session, task: CommunityTaskCreate, user_id: uuid.UUID) -> CommunityTask:
    """创建社区任务"""
    db_task = CommunityTask.model_validate(
        task, update={"id": uuid.uuid4(), "user_id": user_id}
    )
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


def get_community_task(*, session: Session, task_id: uuid.UUID) -> Optional[CommunityTask]:
    """根据ID获取社区任务"""
    return session.get(CommunityTask, task_id)


def get_community_tasks(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 20,
    task_type: Optional[CommunityTaskType] = None,
    status: Optional[CommunityTaskStatus] = None,
    user_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at"  # created_at, expiry_at
) -> Tuple[List[CommunityTaskPublic], int]:
    """获取社区任务列表"""
    query = select(CommunityTask)
    
    # 过滤条件
    conditions = []
    if task_type:
        conditions.append(CommunityTask.task_type == task_type)
    if status:
        conditions.append(CommunityTask.status == status)
    else:
        # 默认只显示开放中的任务
        conditions.append(CommunityTask.status == CommunityTaskStatus.OPEN)
    if user_id:
        conditions.append(CommunityTask.user_id == user_id)
    if search:
        conditions.append(
            or_(
                CommunityTask.title.contains(search),
                CommunityTask.description.contains(search)
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # 排序
    if sort_by == "created_at":
        query = query.order_by(desc(CommunityTask.created_at))
    elif sort_by == "expiry_at":
        query = query.order_by(CommunityTask.expiry_at)
    
    # 分页
    query = query.offset(skip).limit(limit)
    
    # 执行查询
    tasks = session.exec(query).all()
    
    # 获取总数
    count_query = select(func.count()).select_from(CommunityTask)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = session.exec(count_query).one() or 0
    
    # 转换为公开模型
    task_publics = []
    for task in tasks:
        # 获取发布者信息
        publisher = session.get(User, task.user_id)
        publisher_name = publisher.full_name if publisher else None
        publisher_avatar_url = publisher.avatar_url if publisher else None
        
        # 获取申请数量
        application_count = session.exec(
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
        task_publics.append(task_public)
    
    return task_publics, total


def update_community_task(*, session: Session, task: CommunityTask, task_update: CommunityTaskUpdate) -> CommunityTask:
    """更新社区任务"""
    obj_data = task_update.model_dump(exclude_unset=True)
    task.sqlmodel_update(obj_data)
    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def delete_community_task(*, session: Session, task: CommunityTask) -> CommunityTask:
    """删除社区任务"""
    task.status = CommunityTaskStatus.CANCELLED
    task.updated_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


# ==================== 任务申请相关操作 ====================

def create_task_application(*, session: Session, application: TaskApplicationCreate, user_id: uuid.UUID) -> TaskApplication:
    """创建任务申请"""
    # 检查是否已经申请过
    existing = session.exec(
        select(TaskApplication).where(
            and_(
                TaskApplication.task_id == application.task_id,
                TaskApplication.applicant_id == user_id
            )
        )
    ).first()
    
    if existing:
        raise ValueError("您已经申请过这个任务了")
    
    # 检查任务状态
    task = session.get(CommunityTask, application.task_id)
    if not task:
        raise ValueError("任务不存在")
    if task.status != CommunityTaskStatus.OPEN:
        raise ValueError("任务状态不允许申请")
    
    db_application = TaskApplication.model_validate(
        application, update={"id": uuid.uuid4(), "applicant_id": user_id}
    )
    session.add(db_application)
    session.commit()
    session.refresh(db_application)
    return db_application


def get_task_application(*, session: Session, application_id: uuid.UUID) -> Optional[TaskApplication]:
    """根据ID获取任务申请"""
    return session.get(TaskApplication, application_id)


def get_task_applications(
    *,
    session: Session,
    task_id: Optional[uuid.UUID] = None,
    applicant_id: Optional[uuid.UUID] = None,
    status: Optional[ApplicationStatus] = None,
    skip: int = 0,
    limit: int = 20
) -> Tuple[List[TaskApplicationPublic], int]:
    """获取任务申请列表"""
    query = select(TaskApplication)
    
    # 过滤条件
    conditions = []
    if task_id:
        conditions.append(TaskApplication.task_id == task_id)
    if applicant_id:
        conditions.append(TaskApplication.applicant_id == applicant_id)
    if status:
        conditions.append(TaskApplication.status == status)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # 排序
    query = query.order_by(desc(TaskApplication.created_at))
    
    # 分页
    query = query.offset(skip).limit(limit)
    
    # 执行查询
    applications = session.exec(query).all()
    
    # 获取总数
    count_query = select(func.count()).select_from(TaskApplication)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = session.exec(count_query).one() or 0
    
    # 转换为公开模型
    application_publics = []
    for application in applications:
        # 获取申请人信息
        applicant = session.get(User, application.applicant_id)
        applicant_name = applicant.full_name if applicant else None
        applicant_avatar_url = applicant.avatar_url if applicant else None
        
        application_public = TaskApplicationPublic(
            id=application.id,
            task_id=application.task_id,
            applicant_id=application.applicant_id,
            status=application.status,
            apply_message=application.apply_message,
            created_at=application.created_at,
            updated_at=application.updated_at,
            applicant_name=applicant_name,
            applicant_avatar_url=applicant_avatar_url
        )
        application_publics.append(application_public)
    
    return application_publics, total


def update_task_application(*, session: Session, application: TaskApplication, application_update: TaskApplicationUpdate) -> TaskApplication:
    """更新任务申请"""
    obj_data = application_update.model_dump(exclude_unset=True)
    application.sqlmodel_update(obj_data)
    application.updated_at = datetime.utcnow()
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


def accept_task_application(*, session: Session, application: TaskApplication) -> TaskApplication:
    """接受任务申请"""
    # 更新申请状态
    application.status = ApplicationStatus.ACCEPTED
    application.updated_at = datetime.utcnow()
    session.add(application)
    
    # 更新任务状态为进行中
    task = session.get(CommunityTask, application.task_id)
    if task:
        task.status = CommunityTaskStatus.IN_PROGRESS
        task.updated_at = datetime.utcnow()
        session.add(task)
        
        # 拒绝其他申请
        other_applications = session.exec(
            select(TaskApplication).where(
                and_(
                    TaskApplication.task_id == application.task_id,
                    TaskApplication.id != application.id,
                    TaskApplication.status == ApplicationStatus.PENDING
                )
            )
        ).all()
        
        for other_app in other_applications:
            other_app.status = ApplicationStatus.REJECTED
            other_app.updated_at = datetime.utcnow()
            session.add(other_app)
    
    session.commit()
    session.refresh(application)
    return application


def reject_task_application(*, session: Session, application: TaskApplication) -> TaskApplication:
    """拒绝任务申请"""
    application.status = ApplicationStatus.REJECTED
    application.updated_at = datetime.utcnow()
    session.add(application)
    session.commit()
    session.refresh(application)
    return application


# ==================== 评论相关操作 ====================

def create_comment(*, session: Session, comment: CommentCreate, user_id: uuid.UUID) -> Comment:
    """创建评论"""
    db_comment = Comment.model_validate(
        comment, update={"id": uuid.uuid4(), "user_id": user_id}
    )
    session.add(db_comment)
    session.commit()
    session.refresh(db_comment)
    
    # 更新文章评论数
    article = session.get(Article, comment.article_id)
    if article:
        article.comment_count += 1
        session.add(article)
        session.commit()
    
    return db_comment


def get_comment(*, session: Session, comment_id: uuid.UUID) -> Optional[Comment]:
    """根据ID获取评论"""
    return session.get(Comment, comment_id)


def get_comments(
    *,
    session: Session,
    article_id: uuid.UUID,
    parent_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 20
) -> Tuple[List[CommentPublic], int]:
    """获取评论列表"""
    query = select(Comment).where(Comment.article_id == article_id)
    
    if parent_id is None:
        # 获取顶级评论
        query = query.where(Comment.parent_id.is_(None))
    else:
        # 获取指定评论的回复
        query = query.where(Comment.parent_id == parent_id)
    
    # 排序
    query = query.order_by(desc(Comment.created_at))
    
    # 分页
    query = query.offset(skip).limit(limit)
    
    # 执行查询
    comments = session.exec(query).all()
    
    # 获取总数
    count_query = select(func.count()).select_from(Comment).where(Comment.article_id == article_id)
    if parent_id is None:
        count_query = count_query.where(Comment.parent_id.is_(None))
    else:
        count_query = count_query.where(Comment.parent_id == parent_id)
    total = session.exec(count_query).one() or 0
    
    # 转换为公开模型
    comment_publics = []
    for comment in comments:
        # 获取评论者信息
        author = session.get(User, comment.user_id)
        author_name = author.full_name if author else None
        author_avatar_url = author.avatar_url if author else None
        
        # 获取回复数量
        reply_count = session.exec(
            select(func.count()).select_from(Comment).where(
                Comment.parent_id == comment.id
            )
        ).one() or 0
        
        comment_public = CommentPublic(
            id=comment.id,
            article_id=comment.article_id,
            user_id=comment.user_id,
            content=comment.content,
            parent_id=comment.parent_id,
            created_at=comment.created_at,
            author_name=author_name,
            author_avatar_url=author_avatar_url,
            reply_count=reply_count
        )
        comment_publics.append(comment_public)
    
    return comment_publics, total


def delete_comment(*, session: Session, comment: Comment) -> Comment:
    """删除评论"""
    # 更新文章评论数
    article = session.get(Article, comment.article_id)
    if article:
        article.comment_count = max(0, article.comment_count - 1)
        session.add(article)
    
    session.delete(comment)
    session.commit()
    return comment


# ==================== 点赞相关操作 ====================

def create_like(*, session: Session, user_id: uuid.UUID, article_id: uuid.UUID) -> Like:
    """创建点赞记录"""
    # 检查是否已经点赞
    existing = session.get(Like, (user_id, article_id))
    if existing:
        raise ValueError("您已经点赞过了")
    
    db_like = Like(user_id=user_id, article_id=article_id)
    session.add(db_like)
    session.commit()
    session.refresh(db_like)
    
    # 更新文章点赞数
    article = session.get(Article, article_id)
    if article:
        article.like_count += 1
        session.add(article)
        session.commit()
    
    return db_like


def delete_like(*, session: Session, user_id: uuid.UUID, article_id: uuid.UUID) -> Like:
    """取消点赞"""
    like = session.get(Like, (user_id, article_id))
    if not like:
        raise ValueError("您还没有点赞")
    
    session.delete(like)
    session.commit()
    
    # 更新文章点赞数
    article = session.get(Article, article_id)
    if article:
        article.like_count = max(0, article.like_count - 1)
        session.add(article)
        session.commit()
    
    return like


def get_like(*, session: Session, user_id: uuid.UUID, article_id: uuid.UUID) -> Optional[Like]:
    """获取点赞记录"""
    return session.get(Like, (user_id, article_id))


def get_likes(
    *,
    session: Session,
    article_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 20
) -> Tuple[List[LikePublic], int]:
    """获取点赞列表"""
    query = select(Like)
    
    # 过滤条件
    conditions = []
    if article_id:
        conditions.append(Like.article_id == article_id)
    if user_id:
        conditions.append(Like.user_id == user_id)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # 排序
    query = query.order_by(desc(Like.created_at))
    
    # 分页
    query = query.offset(skip).limit(limit)
    
    # 执行查询
    likes = session.exec(query).all()
    
    # 获取总数
    count_query = select(func.count()).select_from(Like)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = session.exec(count_query).one() or 0
    
    # 转换为公开模型
    like_publics = []
    for like in likes:
        # 获取用户信息
        user = session.get(User, like.user_id)
        user_name = user.full_name if user else None
        user_avatar_url = user.avatar_url if user else None
        
        like_public = LikePublic(
            user_id=like.user_id,
            article_id=like.article_id,
            created_at=like.created_at,
            user_name=user_name,
            user_avatar_url=user_avatar_url
        )
        like_publics.append(like_public)
    
    return like_publics, total


# ==================== 热度计算相关操作 ====================

def calculate_article_hot_score(*, session: Session, article: Article) -> float:
    """计算文章热度分"""
    # 基础分数
    base_score = 0.0
    
    # 浏览数权重
    base_score += article.view_count * 0.1
    
    # 点赞数权重
    base_score += article.like_count * 1.0
    
    # 评论数权重
    base_score += article.comment_count * 2.0
    
    # 分享数权重
    base_score += article.share_count * 3.0
    
    # 时间衰减因子（越新的文章分数越高）
    time_diff = datetime.utcnow() - article.created_at
    hours_ago = time_diff.total_seconds() / 3600
    time_factor = max(0.1, 1.0 - (hours_ago / 168))  # 一周内的时间衰减
    
    hot_score = base_score * time_factor
    
    return round(hot_score, 2)


def update_all_article_hot_scores(*, session: Session) -> int:
    """更新所有文章的热度分"""
    articles = session.exec(select(Article).where(Article.status == ArticleStatus.PUBLISHED)).all()
    
    updated_count = 0
    for article in articles:
        hot_score = calculate_article_hot_score(session=session, article=article)
        article.hot_score = hot_score
        session.add(article)
        updated_count += 1
    
    session.commit()
    return updated_count
