"""
初始化积分系统数据
"""
import json
import os
from datetime import datetime
from typing import List

from sqlmodel import Session, select

from app.core.db import engine
from app.models import Task, TaskType


def load_tasks_data() -> List[dict]:
    """加载任务数据"""
    data_file = os.path.join(os.path.dirname(__file__), "data", "tasks_data.json")
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_tasks_data():
    """清空所有任务数据"""
    with Session(engine) as session:
        # 删除所有任务
        statement = select(Task)
        tasks = session.exec(statement).all()
        for task in tasks:
            session.delete(task)
        session.commit()
        print("✅ 已清空所有任务数据")


def show_tasks_summary():
    """显示任务数据摘要"""
    with Session(engine) as session:
        statement = select(Task)
        tasks = session.exec(statement).all()
        
        print(f"📊 任务数据摘要:")
        print(f"   总数量: {len(tasks)}")
        
        # 按类型分组统计
        type_stats = {}
        for task in tasks:
            task_type = task.task_type.value
            if task_type not in type_stats:
                type_stats[task_type] = {"count": 0, "active": 0}
            type_stats[task_type]["count"] += 1
            if task.is_active:
                type_stats[task_type]["active"] += 1
        
        type_names = {
            "one_time": "一次性任务",
            "daily": "每日任务", 
            "weekly": "每周任务",
            "monthly": "每月任务",
            "repeatable": "可重复任务"
        }
        
        for task_type, stats in type_stats.items():
            type_name = type_names.get(task_type, f"类型{task_type}")
            print(f"   {type_name}: {stats['count']} 个 (激活: {stats['active']})")
        
        # 按积分奖励分组统计
        points_stats = {}
        for task in tasks:
            points = task.points_reward
            if points not in points_stats:
                points_stats[points] = 0
            points_stats[points] += 1
        
        print(f"   积分奖励分布:")
        for points in sorted(points_stats.keys()):
            print(f"     {points}积分: {points_stats[points]} 个任务")


def insert_tasks_data():
    """插入任务数据"""
    tasks_data = load_tasks_data()
    
    with Session(engine) as session:
        inserted_count = 0
        skipped_count = 0
        
        for task_data in tasks_data:
            # 检查是否已存在相同的任务代码
            existing_statement = select(Task).where(
                Task.task_code == task_data["task_code"]
            )
            existing = session.exec(existing_statement).first()
            
            if existing:
                print(f"   ⏭️  跳过已存在的任务: {task_data['task_code']}")
                skipped_count += 1
                continue
            
            # 创建任务
            task = Task(
                task_code=task_data["task_code"],
                title=task_data["title"],
                description=task_data["description"],
                points_reward=task_data["points_reward"],
                task_type=TaskType(task_data["task_type"]),
                is_active=task_data["is_active"],
                max_completions=task_data.get("max_completions"),
                cooldown_hours=task_data.get("cooldown_hours"),
                start_date=datetime.fromisoformat(task_data["start_date"]) if task_data.get("start_date") else None,
                end_date=datetime.fromisoformat(task_data["end_date"]) if task_data.get("end_date") else None,
                conditions=task_data.get("conditions"),
                button_text=task_data.get("button_text"),
                uri=task_data.get("uri")
            )
            
            session.add(task)
            inserted_count += 1
            print(f"   ✅ 创建任务: {task_data['title']} ({task_data['points_reward']}积分)")
        
        session.commit()
        print(f"\n🎉 任务数据插入完成!")
        print(f"   新增: {inserted_count} 个")
        print(f"   跳过: {skipped_count} 个")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--clear":
            clear_tasks_data()
        elif sys.argv[1] == "--summary":
            show_tasks_summary()
        else:
            print("用法: python initial_points_data.py [--clear|--summary]")
    else:
        insert_tasks_data()
