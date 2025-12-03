import json
import os
from datetime import datetime
from typing import List

from sqlmodel import Session, select

from app.core.db import engine
from app.models import MembershipBenefit, MembershipBenefitCreate, User


def load_membership_benefits_data() -> List[dict]:
    """加载会员权益数据"""
    data_file = os.path.join(os.path.dirname(__file__), "data", "membership_benefits_data.json")
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


def clear_membership_benefits_data():
    """清空所有会员权益数据"""
    with Session(engine) as session:
        # 删除所有会员权益
        statement = select(MembershipBenefit)
        membership_benefits = session.exec(statement).all()
        for membership_benefit in membership_benefits:
            session.delete(membership_benefit)
        session.commit()
        print("✅ 已清空所有会员权益数据")


def show_membership_benefits_summary():
    """显示会员权益数据摘要"""
    with Session(engine) as session:
        statement = select(MembershipBenefit)
        membership_benefits = session.exec(statement).all()
        
        print(f"📊 会员权益数据摘要:")
        print(f"   总数量: {len(membership_benefits)}")
        
        # 按用户分组统计
        user_stats = {}
        for benefit in membership_benefits:
            user_id = str(benefit.user_id)
            if user_id not in user_stats:
                user_stats[user_id] = {"count": 0, "providers": set()}
            user_stats[user_id]["count"] += 1
            user_stats[user_id]["providers"].add(benefit.provider_id)
        
        print(f"   涉及用户: {len(user_stats)}")
        for user_id, stats in user_stats.items():
            print(f"   用户 {user_id[:8]}...: {stats['count']} 个权益 ({', '.join(stats['providers'])})")


def insert_membership_benefits_data():
    """插入会员权益数据"""
    configs = load_membership_benefits_data()
    
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
            
            print(f"📱 为用户 {user.phone} 创建会员权益...")
            
            for benefit_data in user_config["membership_benefits"]:
                # 检查是否已存在相同的权益
                existing_statement = select(MembershipBenefit).where(
                    MembershipBenefit.user_id == user.id,
                    MembershipBenefit.benefit_name == benefit_data["benefit_name"],
                    MembershipBenefit.provider_id == benefit_data["provider_id"]
                )
                existing = session.exec(existing_statement).first()
                
                if existing:
                    print(f"   ⏭️  跳过已存在的权益: {benefit_data['benefit_name']}")
                    skipped_count += 1
                    continue
                
                # 创建会员权益
                membership_benefit_create = MembershipBenefitCreate(
                    user_id=user.id,
                    benefit_name=benefit_data["benefit_name"],
                    provider_id=benefit_data["provider_id"],
                    description=benefit_data["description"],
                    total_duration_days=benefit_data["total_duration_days"],
                    activation_date=datetime.fromisoformat(benefit_data["activation_date"]),
                    expiration_date=datetime.fromisoformat(benefit_data["expiration_date"]),
                    status=benefit_data["status"],
                    ui_config_json=benefit_data.get("ui_config_json")
                )
                
                membership_benefit = MembershipBenefit.model_validate(membership_benefit_create)
                session.add(membership_benefit)
                inserted_count += 1
                print(f"   ✅ 创建权益: {benefit_data['benefit_name']} ({benefit_data['provider_id']})")
        
        session.commit()
        print(f"\n🎉 会员权益数据插入完成!")
        print(f"   新增: {inserted_count} 个")
        print(f"   跳过: {skipped_count} 个")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--clear":
            clear_membership_benefits_data()
        elif sys.argv[1] == "--summary":
            show_membership_benefits_summary()
        else:
            print("用法: python initial_membership_benefits_data.py [--clear|--summary]")
    else:
        insert_membership_benefits_data()
