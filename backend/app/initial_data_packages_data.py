import json
import os
from datetime import datetime
from typing import List

from sqlmodel import Session, select

from app.core.db import engine
from app.models import DataPackage, DataPackageCreate, User


def load_data_packages_data() -> List[dict]:
    """加载流量包数据"""
    data_file = os.path.join(os.path.dirname(__file__), "data", "data_packages_data.json")
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def find_matching_user_config(phone: str, configs: List[dict]) -> dict:
    """根据手机号找到匹配的用户配置"""
    for config in configs:
        pattern = config["user_phone_pattern"]
        # 精确匹配或模式匹配
        if phone == pattern:
            return config
        # 如果模式包含*，进行模糊匹配
        elif "*" in pattern:
            # 简单的模式匹配逻辑
            if phone and pattern.replace("*", "") in phone.replace("*", ""):
                return config
    return None


def clear_data_packages_data():
    """清空所有流量包数据"""
    with Session(engine) as session:
        # 删除所有流量包
        statement = select(DataPackage)
        data_packages = session.exec(statement).all()
        for data_package in data_packages:
            session.delete(data_package)
        session.commit()
        print("✅ 已清空所有流量包数据")


def show_data_packages_summary():
    """显示流量包数据摘要"""
    with Session(engine) as session:
        statement = select(DataPackage)
        data_packages = session.exec(statement).all()
        
        print(f"📊 流量包数据摘要:")
        print(f"   总数量: {len(data_packages)}")
        
        # 按用户分组统计
        user_stats = {}
        for pkg in data_packages:
            user_id = str(pkg.user_id)
            if user_id not in user_stats:
                user_stats[user_id] = {"count": 0, "types": set()}
            user_stats[user_id]["count"] += 1
            user_stats[user_id]["types"].add(pkg.package_type)
        
        print(f"   涉及用户: {len(user_stats)}")
        for user_id, stats in user_stats.items():
            print(f"   用户 {user_id[:8]}...: {stats['count']} 个流量包 ({', '.join(stats['types'])})")


def insert_data_packages_data():
    """插入流量包数据"""
    configs = load_data_packages_data()
    
    with Session(engine) as session:
        # 获取所有用户
        statement = select(User)
        users = session.exec(statement).all()
        
        inserted_count = 0
        skipped_count = 0
        
        for user in users:
            if not user.phone:
                continue
                
            # 查找匹配的配置
            user_config = find_matching_user_config(user.phone, configs)
            if not user_config:
                continue
            
            print(f"📱 为用户 {user.phone} 创建流量包...")
            
            for pkg_data in user_config["data_packages"]:
                # 检查是否已存在相同的流量包
                existing_statement = select(DataPackage).where(
                    DataPackage.user_id == user.id,
                    DataPackage.package_name == pkg_data["package_name"],
                    DataPackage.package_type == pkg_data["package_type"]
                )
                existing = session.exec(existing_statement).first()
                
                if existing:
                    print(f"   ⏭️  跳过已存在的流量包: {pkg_data['package_name']}")
                    skipped_count += 1
                    continue
                
                # 创建流量包
                data_package_create = DataPackageCreate(
                    user_id=user.id,
                    package_name=pkg_data["package_name"],
                    package_type=pkg_data["package_type"],
                    total_mb=pkg_data["total_mb"],
                    used_mb=pkg_data["used_mb"],
                    expiration_date=datetime.fromisoformat(pkg_data["expiration_date"]),
                    is_shared=pkg_data["is_shared"],
                    status=pkg_data["status"]
                )
                
                data_package = DataPackage.model_validate(data_package_create)
                session.add(data_package)
                inserted_count += 1
                print(f"   ✅ 创建流量包: {pkg_data['package_name']} ({pkg_data['package_type']})")
        
        session.commit()
        print(f"\n🎉 流量包数据插入完成!")
        print(f"   新增: {inserted_count} 个")
        print(f"   跳过: {skipped_count} 个")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--clear":
            clear_data_packages_data()
        elif sys.argv[1] == "--summary":
            show_data_packages_summary()
        else:
            print("用法: python initial_data_packages_data.py [--clear|--summary]")
    else:
        insert_data_packages_data()
