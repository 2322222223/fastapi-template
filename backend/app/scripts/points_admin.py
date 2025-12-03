"""
积分系统管理脚本
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Task, TaskType, User, PointsTransaction, CheckInHistory
from app.crud_points import get_points_leaderboard, get_user_points_stats
from app.services_points import create_points_service
# 工具函数内联定义
def format_points_display(points: int) -> str:
    """格式化积分显示"""
    if points >= 10000:
        return f"{points / 10000:.1f}万"
    elif points >= 1000:
        return f"{points / 1000:.1f}千"
    else:
        return str(points)


def get_points_achievement_level(points: int) -> dict:
    """获取积分成就等级"""
    levels = [
        {"min_points": 0, "max_points": 99, "name": "新手", "icon": "🌱", "color": "#8B4513"},
        {"min_points": 100, "max_points": 499, "name": "青铜", "icon": "🥉", "color": "#CD7F32"},
        {"min_points": 500, "max_points": 999, "name": "白银", "icon": "🥈", "color": "#C0C0C0"},
        {"min_points": 1000, "max_points": 4999, "name": "黄金", "icon": "🥇", "color": "#FFD700"},
        {"min_points": 5000, "max_points": 9999, "name": "铂金", "icon": "💎", "color": "#E5E4E2"},
        {"min_points": 10000, "max_points": 49999, "name": "钻石", "icon": "💠", "color": "#B9F2FF"},
        {"min_points": 50000, "max_points": 99999, "name": "大师", "icon": "👑", "color": "#FF6B6B"},
        {"min_points": 100000, "max_points": float('inf'), "name": "传奇", "icon": "🌟", "color": "#FFD700"}
    ]
    
    for level in levels:
        if level["min_points"] <= points <= level["max_points"]:
            next_level = None
            for next_lvl in levels:
                if next_lvl["min_points"] > points:
                    next_level = next_lvl
                    break
            
            return {
                "current_level": level,
                "next_level": next_level,
                "points_to_next": next_level["min_points"] - points if next_level else 0,
                "progress_percentage": min(100, ((points - level["min_points"]) / (level["max_points"] - level["min_points"] + 1)) * 100)
            }
    
    return {
        "current_level": levels[0],
        "next_level": levels[1],
        "points_to_next": 100,
        "progress_percentage": 0
    }


def create_task(
    task_code: str,
    title: str,
    description: str,
    points_reward: int,
    task_type: str,
    max_completions: Optional[int] = None,
    cooldown_hours: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> None:
    """创建新任务"""
    db: Session = SessionLocal()
    try:
        # 检查任务代码是否已存在
        existing_task = db.query(Task).filter(Task.task_code == task_code).first()
        if existing_task:
            print(f"任务代码 '{task_code}' 已存在")
            return
        
        # 创建任务
        task = Task(
            task_code=task_code,
            title=title,
            description=description,
            points_reward=points_reward,
            task_type=TaskType(task_type),
            is_active=True,
            max_completions=max_completions,
            cooldown_hours=cooldown_hours,
            start_date=start_date,
            end_date=end_date
        )
        
        db.add(task)
        db.commit()
        print(f"成功创建任务: {title} ({task_code})")
        
    except Exception as e:
        print(f"创建任务时出错: {e}")
        db.rollback()
    finally:
        db.close()


def list_tasks() -> None:
    """列出所有任务"""
    db: Session = SessionLocal()
    try:
        tasks = db.query(Task).all()
        
        if not tasks:
            print("没有找到任何任务")
            return
        
        print(f"\n找到 {len(tasks)} 个任务:")
        print("-" * 80)
        for task in tasks:
            status = "活跃" if task.is_active else "停用"
            print(f"ID: {task.id}")
            print(f"代码: {task.task_code}")
            print(f"标题: {task.title}")
            print(f"类型: {task.task_type.value}")
            print(f"积分奖励: {task.points_reward}")
            print(f"状态: {status}")
            print(f"最大完成次数: {task.max_completions or '无限制'}")
            print(f"冷却时间: {task.cooldown_hours or 0} 小时")
            print(f"开始时间: {task.start_date or '无限制'}")
            print(f"结束时间: {task.end_date or '无限制'}")
            print("-" * 80)
            
    except Exception as e:
        print(f"列出任务时出错: {e}")
    finally:
        db.close()


def show_leaderboard(limit: int = 10) -> None:
    """显示积分排行榜"""
    db: Session = SessionLocal()
    try:
        leaderboard, total, _ = get_points_leaderboard(session=db, limit=limit)
        
        print(f"\n积分排行榜 (前{limit}名):")
        print("-" * 60)
        for entry in leaderboard:
            print(f"第{entry.rank}名: {entry.full_name or '匿名用户'}")
            print(f"  积分: {format_points_display(entry.points_balance)}")
            print(f"  连续签到: {entry.consecutive_check_in_days}天")
            print("-" * 60)
            
    except Exception as e:
        print(f"显示排行榜时出错: {e}")
    finally:
        db.close()


def show_user_stats(user_id: str) -> None:
    """显示用户积分统计"""
    db: Session = SessionLocal()
    try:
        user_uuid = uuid.UUID(user_id)
        user = db.get(User, user_uuid)
        
        if not user:
            print(f"用户 {user_id} 不存在")
            return
        
        stats = get_user_points_stats(session=db, user_id=user_uuid)
        achievement = get_points_achievement_level(stats.total_points)
        
        print(f"\n用户积分统计: {user.full_name or user.email}")
        print("-" * 50)
        print(f"总积分: {format_points_display(stats.total_points)}")
        print(f"当前排名: {stats.current_rank or '未上榜'}")
        print(f"连续签到天数: {stats.consecutive_check_in_days}")
        print(f"总签到次数: {stats.total_check_ins}")
        print(f"完成任务数: {stats.total_tasks_completed}")
        print(f"本月积分: {format_points_display(stats.points_this_month)}")
        print(f"本周积分: {format_points_display(stats.points_this_week)}")
        print(f"今日积分: {format_points_display(stats.points_today)}")
        print(f"成就等级: {achievement['current_level']['name']} {achievement['current_level']['icon']}")
        print(f"距离下一等级: {achievement['points_to_next']} 积分")
        
    except ValueError:
        print("无效的用户ID格式")
    except Exception as e:
        print(f"显示用户统计时出错: {e}")
    finally:
        db.close()


def show_system_stats() -> None:
    """显示系统统计信息"""
    db: Session = SessionLocal()
    try:
        # 用户统计
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        # 积分统计
        total_points = db.query(PointsTransaction).filter(PointsTransaction.points_change > 0).count()
        total_check_ins = db.query(CheckInHistory).count()
        
        # 任务统计
        total_tasks = db.query(Task).count()
        active_tasks = db.query(Task).filter(Task.is_active == True).count()
        
        print(f"\n系统统计信息:")
        print("-" * 40)
        print(f"总用户数: {total_users}")
        print(f"活跃用户数: {active_users}")
        print(f"总积分交易数: {total_points}")
        print(f"总签到次数: {total_check_ins}")
        print(f"总任务数: {total_tasks}")
        print(f"活跃任务数: {active_tasks}")
        
    except Exception as e:
        print(f"显示系统统计时出错: {e}")
    finally:
        db.close()


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python points_admin.py <command> [args...]")
        print("命令:")
        print("  create_task <task_code> <title> <description> <points> <type> [max_completions] [cooldown_hours]")
        print("  list_tasks")
        print("  leaderboard [limit]")
        print("  user_stats <user_id>")
        print("  system_stats")
        return
    
    command = sys.argv[1]
    
    if command == "create_task":
        if len(sys.argv) < 7:
            print("用法: create_task <task_code> <title> <description> <points> <type> [max_completions] [cooldown_hours]")
            return
        
        task_code = sys.argv[2]
        title = sys.argv[3]
        description = sys.argv[4]
        points = int(sys.argv[5])
        task_type = sys.argv[6]
        max_completions = int(sys.argv[7]) if len(sys.argv) > 7 else None
        cooldown_hours = int(sys.argv[8]) if len(sys.argv) > 8 else None
        
        create_task(task_code, title, description, points, task_type, max_completions, cooldown_hours)
        
    elif command == "list_tasks":
        list_tasks()
        
    elif command == "leaderboard":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        show_leaderboard(limit)
        
    elif command == "user_stats":
        if len(sys.argv) < 3:
            print("用法: user_stats <user_id>")
            return
        user_id = sys.argv[2]
        show_user_stats(user_id)
        
    elif command == "system_stats":
        show_system_stats()
        
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()
