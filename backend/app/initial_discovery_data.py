#!/usr/bin/env python3
"""
初始化发现页面测试数据
"""
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

from app.core.db import engine
from app.models import (
    User, Article, CommunityTask, TaskApplication, Comment, Like,
    ArticleType, ArticleStatus, CommunityTaskType, CommunityTaskStatus, ApplicationStatus
)


def load_test_data():
    """加载测试数据"""
    data_file = Path(__file__).parent / "data" / "discovery_test_data.json"
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_or_create_test_users(session: Session):
    """获取或创建测试用户"""
    # 查找现有的测试用户（通过邮箱前缀匹配）
    test_users = session.exec(
        select(User).where(User.email.like("admin%@herenow.com"))
    ).all()
    
    if len(test_users) >= 4:
        return test_users[:4]
    
    # 创建测试用户
    users = []
    for i in range(4):
        # 检查用户是否已存在
        existing_user = session.exec(
            select(User).where(User.email == f"admin{i+1}@herenow.com")
        ).first()
        
        if existing_user:
            users.append(existing_user)
            continue
            
        user = User(
            email=f"admin{i+1}@herenow.com",
            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
            full_name=f"测试用户{i+1}",
            is_active=True,
            is_superuser=False,
            points_balance=1000,
            invite_code=f"TEST{i+1:03d}"
        )
        session.add(user)
        users.append(user)
    
    session.commit()
    for user in users:
        session.refresh(user)
    
    return users


def insert_articles(session: Session, users: list[User], articles_data: list[dict]):
    """插入文章数据"""
    # 检查是否已有文章数据
    existing_articles = session.exec(select(Article)).first()
    if existing_articles:
        print("文章数据已存在，跳过插入")
        return
    
    print("开始插入文章数据...")
    
    for i, article_data in enumerate(articles_data):
        # 轮换使用用户作为作者
        author = users[i % len(users)]
        
        article = Article(
            id=uuid.uuid4(),
            user_id=author.id,
            title=article_data["title"],
            content=article_data["content"],
            cover_image_url=article_data.get("cover_image_url"),
            type=ArticleType(article_data["type"]),
            status=ArticleStatus(article_data["status"]),
            view_count=article_data.get("view_count", 0),
            like_count=article_data.get("like_count", 0),
            comment_count=article_data.get("comment_count", 0),
            share_count=article_data.get("share_count", 0),
            hot_score=article_data.get("hot_score", 0.0),
            created_at=datetime.utcnow() - timedelta(hours=24-i*2),  # 模拟不同发布时间
            updated_at=datetime.utcnow() - timedelta(hours=24-i*2)
        )
        session.add(article)
    
    session.commit()
    print(f"成功插入 {len(articles_data)} 篇文章")


def insert_community_tasks(session: Session, users: list[User], tasks_data: list[dict]):
    """插入社区任务数据"""
    # 检查是否已有任务数据
    existing_tasks = session.exec(select(CommunityTask)).first()
    if existing_tasks:
        print("社区任务数据已存在，跳过插入")
        return
    
    print("开始插入社区任务数据...")
    
    for i, task_data in enumerate(tasks_data):
        # 轮换使用用户作为发布者
        publisher = users[i % len(users)]
        
        # 解析过期时间
        expiry_at = None
        if task_data.get("expiry_at"):
            expiry_at = datetime.fromisoformat(task_data["expiry_at"].replace("Z", "+00:00"))
        
        task = CommunityTask(
            id=uuid.uuid4(),
            user_id=publisher.id,
            title=task_data["title"],
            description=task_data["description"],
            task_type=CommunityTaskType(task_data["task_type"]),
            status=CommunityTaskStatus(task_data["status"]),
            reward_info=task_data.get("reward_info"),
            contact_info=task_data.get("contact_info"),
            expiry_at=expiry_at,
            created_at=datetime.utcnow() - timedelta(hours=48-i*6),  # 模拟不同发布时间
            updated_at=datetime.utcnow() - timedelta(hours=48-i*6)
        )
        session.add(task)
    
    session.commit()
    print(f"成功插入 {len(tasks_data)} 个社区任务")


def insert_comments(session: Session, users: list[User], comments_data: list[dict]):
    """插入评论数据"""
    # 检查是否已有评论数据
    existing_comments = session.exec(select(Comment)).first()
    if existing_comments:
        print("评论数据已存在，跳过插入")
        return
    
    print("开始插入评论数据...")
    
    # 获取文章列表
    articles = session.exec(select(Article)).all()
    if not articles:
        print("没有找到文章，跳过评论插入")
        return
    
    for i, comment_data in enumerate(comments_data):
        # 轮换使用用户作为评论者
        commenter = users[i % len(users)]
        
        # 轮换使用文章
        article = articles[i % len(articles)]
        
        comment = Comment(
            id=uuid.uuid4(),
            article_id=article.id,
            user_id=commenter.id,
            content=comment_data["content"],
            parent_id=None,  # 暂时不处理回复关系
            created_at=datetime.utcnow() - timedelta(hours=12-i*2)
        )
        session.add(comment)
    
    session.commit()
    print(f"成功插入 {len(comments_data)} 条评论")


def insert_likes(session: Session, users: list[User], likes_data: list[dict]):
    """插入点赞数据"""
    # 检查是否已有点赞数据
    existing_likes = session.exec(select(Like)).first()
    if existing_likes:
        print("点赞数据已存在，跳过插入")
        return
    
    print("开始插入点赞数据...")
    
    # 获取文章列表
    articles = session.exec(select(Article)).all()
    if not articles:
        print("没有找到文章，跳过点赞插入")
        return
    
    for like_data in likes_data:
        # 这里简化处理，直接使用索引
        try:
            user_index = int(like_data["user_id"].replace("user", "")) - 1
            article_index = int(like_data["article_id"].replace("article", "")) - 1
            
            if 0 <= user_index < len(users) and 0 <= article_index < len(articles):
                user = users[user_index]
                article = articles[article_index]
                
                like = Like(
                    user_id=user.id,
                    article_id=article.id,
                    created_at=datetime.utcnow() - timedelta(hours=6)
                )
                session.add(like)
        except (ValueError, IndexError):
            continue
    
    session.commit()
    print(f"成功插入点赞数据")


def insert_task_applications(session: Session, users: list[User]):
    """插入任务申请数据"""
    # 检查是否已有申请数据
    existing_applications = session.exec(select(TaskApplication)).first()
    if existing_applications:
        print("任务申请数据已存在，跳过插入")
        return
    
    print("开始插入任务申请数据...")
    
    # 获取开放中的任务
    open_tasks = session.exec(
        select(CommunityTask).where(CommunityTask.status == CommunityTaskStatus.OPEN)
    ).all()
    
    if not open_tasks:
        print("没有找到开放中的任务，跳过申请插入")
        return
    
    # 为每个开放的任务创建1-2个申请
    for task in open_tasks:
        # 随机选择1-2个用户申请（排除任务发布者）
        applicants = [user for user in users if user.id != task.user_id]
        num_applications = min(2, len(applicants))
        
        for i in range(num_applications):
            applicant = applicants[i]
            
            application = TaskApplication(
                id=uuid.uuid4(),
                task_id=task.id,
                applicant_id=applicant.id,
                status=ApplicationStatus.PENDING,
                apply_message=f"我对这个任务很感兴趣，希望能与您合作。",
                created_at=datetime.utcnow() - timedelta(hours=24-i*12)
            )
            session.add(application)
    
    session.commit()
    print("成功插入任务申请数据")


def main():
    """主函数"""
    print("开始初始化发现页面测试数据...")
    
    # 加载测试数据
    test_data = load_test_data()
    
    with Session(engine) as session:
        try:
            # 获取或创建测试用户
            users = get_or_create_test_users(session)
            print(f"使用 {len(users)} 个测试用户")
            
            # 插入文章数据
            insert_articles(session, users, test_data["articles"])
            
            # 插入社区任务数据
            insert_community_tasks(session, users, test_data["community_tasks"])
            
            # 插入评论数据
            insert_comments(session, users, test_data["comments"])
            
            # 插入点赞数据
            insert_likes(session, users, test_data["likes"])
            
            # 插入任务申请数据
            insert_task_applications(session, users)
            
            print("发现页面测试数据初始化完成!")
            
        except Exception as e:
            print(f"初始化数据时出错: {e}")
            session.rollback()
            raise


if __name__ == "__main__":
    main()
