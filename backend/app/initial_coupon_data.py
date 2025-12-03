import json
import os
import uuid
from datetime import datetime
from typing import List

from sqlmodel import Session, select

from app.core.db import engine
from app.models import CouponTemplate, CouponTemplateCreate, User, UserCoupon, UserCouponCreate


def load_coupon_templates_data() -> List[dict]:
    """加载优惠券模板数据"""
    data_file = os.path.join(os.path.dirname(__file__), "data", "coupon_templates_data.json")
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_user_coupons_data() -> List[dict]:
    """加载用户优惠券数据"""
    data_file = os.path.join(os.path.dirname(__file__), "data", "user_coupons_data.json")
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


def clear_coupon_templates_data():
    """清空所有优惠券模板数据"""
    with Session(engine) as session:
        # 删除所有优惠券模板
        statement = select(CouponTemplate)
        templates = session.exec(statement).all()
        for template in templates:
            session.delete(template)
        session.commit()
        print("✅ 已清空所有优惠券模板数据")


def clear_user_coupons_data():
    """清空所有用户优惠券数据"""
    with Session(engine) as session:
        # 删除所有用户优惠券
        statement = select(UserCoupon)
        coupons = session.exec(statement).all()
        for coupon in coupons:
            session.delete(coupon)
        session.commit()
        print("✅ 已清空所有用户优惠券数据")


def show_coupon_templates_summary():
    """显示优惠券模板数据摘要"""
    with Session(engine) as session:
        statement = select(CouponTemplate)
        templates = session.exec(statement).all()
        
        print(f"📊 优惠券模板数据摘要:")
        print(f"   总数量: {len(templates)}")
        
        # 按类型分组统计
        type_stats = {}
        for template in templates:
            coupon_type = template.coupon_type
            if coupon_type not in type_stats:
                type_stats[coupon_type] = {"count": 0, "active": 0}
            type_stats[coupon_type]["count"] += 1
            if template.is_active:
                type_stats[coupon_type]["active"] += 1
        
        type_names = {1: "满减券", 2: "折扣券", 3: "运费抵扣券", 4: "兑换券"}
        for coupon_type, stats in type_stats.items():
            type_name = type_names.get(coupon_type, f"类型{coupon_type}")
            print(f"   {type_name}: {stats['count']} 个 (激活: {stats['active']})")


def show_user_coupons_summary():
    """显示用户优惠券数据摘要"""
    with Session(engine) as session:
        statement = select(UserCoupon)
        coupons = session.exec(statement).all()
        
        print(f"📊 用户优惠券数据摘要:")
        print(f"   总数量: {len(coupons)}")
        
        # 按状态分组统计
        status_stats = {0: 0, 1: 0, 2: 0, 3: 0}
        for coupon in coupons:
            status_stats[coupon.status] += 1
        
        status_names = {0: "未使用", 1: "已使用", 2: "已过期", 3: "冻结中"}
        for status, count in status_stats.items():
            print(f"   {status_names[status]}: {count} 个")
        
        # 按用户分组统计
        user_stats = {}
        for coupon in coupons:
            user_id = str(coupon.user_id)
            if user_id not in user_stats:
                user_stats[user_id] = 0
            user_stats[user_id] += 1
        
        print(f"   涉及用户: {len(user_stats)}")
        for user_id, count in list(user_stats.items())[:5]:  # 只显示前5个用户
            print(f"   用户 {user_id[:8]}...: {count} 张优惠券")


def insert_coupon_templates_data():
    """插入优惠券模板数据"""
    templates_data = load_coupon_templates_data()
    
    with Session(engine) as session:
        inserted_count = 0
        skipped_count = 0
        
        for template_data in templates_data:
            # 检查是否已存在相同的模板
            existing_statement = select(CouponTemplate).where(
                CouponTemplate.title == template_data["title"]
            )
            existing = session.exec(existing_statement).first()
            
            if existing:
                print(f"   ⏭️  跳过已存在的模板: {template_data['title']}")
                skipped_count += 1
                continue
            
            # 创建优惠券模板
            template_create = CouponTemplateCreate(
                title=template_data["title"],
                coupon_type=template_data["coupon_type"],
                value=template_data["value"],
                min_spend=template_data["min_spend"],
                description=template_data["description"],
                usage_scope_desc=template_data["usage_scope_desc"],
                total_quantity=template_data["total_quantity"],
                issued_quantity=template_data["issued_quantity"],
                validity_type=template_data["validity_type"],
                valid_days=template_data.get("valid_days"),
                fixed_start_time=datetime.fromisoformat(template_data["fixed_start_time"]) if template_data.get("fixed_start_time") else None,
                fixed_end_time=datetime.fromisoformat(template_data["fixed_end_time"]) if template_data.get("fixed_end_time") else None,
                is_active=template_data["is_active"]
            )
            
            template = CouponTemplate.model_validate(template_create)
            session.add(template)
            inserted_count += 1
            print(f"   ✅ 创建模板: {template_data['title']}")
        
        session.commit()
        print(f"\n🎉 优惠券模板数据插入完成!")
        print(f"   新增: {inserted_count} 个")
        print(f"   跳过: {skipped_count} 个")


def insert_user_coupons_data():
    """插入用户优惠券数据"""
    configs = load_user_coupons_data()
    
    with Session(engine) as session:
        # 获取所有用户
        statement = select(User)
        users = session.exec(statement).all()
        
        # 获取所有模板
        template_statement = select(CouponTemplate)
        templates = session.exec(template_statement).all()
        template_map = {template.title: template for template in templates}
        
        inserted_count = 0
        skipped_count = 0
        
        for user in users:
            if not user.phone:
                continue
                
            # 查找匹配的配置
            user_config = find_matching_user_config(user.phone, configs)
            if not user_config:
                continue
            
            print(f"📱 为用户 {user.phone} 创建优惠券...")
            
            for coupon_data in user_config["user_coupons"]:
                # 查找对应的模板
                template = template_map.get(coupon_data["template_title"])
                if not template:
                    print(f"   ⚠️  模板不存在: {coupon_data['template_title']}")
                    continue
                
                # 检查是否已存在相同的优惠券
                existing_statement = select(UserCoupon).where(
                    UserCoupon.user_id == user.id,
                    UserCoupon.coupon_template_id == template.id,
                    UserCoupon.coupon_code == coupon_data.get("coupon_code")
                )
                existing = session.exec(existing_statement).first()
                
                if existing:
                    print(f"   ⏭️  跳过已存在的优惠券: {coupon_data['template_title']}")
                    skipped_count += 1
                    continue
                
                # 创建用户优惠券
                user_coupon = UserCoupon(
                    user_id=user.id,
                    coupon_template_id=template.id,
                    title=coupon_data["template_title"],
                    status=coupon_data["status"],
                    coupon_code=coupon_data.get("coupon_code"),
                    coupon_type=coupon_data["coupon_type"],
                    value=coupon_data["value"],
                    min_spend=coupon_data["min_spend"],
                    description=coupon_data["description"],
                    usage_scope_desc=coupon_data["usage_scope_desc"],
                    detailed_instructions=coupon_data.get("detailed_instructions"),
                    start_time=datetime.fromisoformat(coupon_data["start_time"]),
                    end_time=datetime.fromisoformat(coupon_data["end_time"]),
                    used_time=datetime.fromisoformat(coupon_data["used_time"]) if coupon_data.get("used_time") else None,
                    order_id=uuid.UUID(coupon_data["order_id"]) if coupon_data.get("order_id") else None
                )
                
                session.add(user_coupon)
                inserted_count += 1
                print(f"   ✅ 创建优惠券: {coupon_data['template_title']} (状态: {coupon_data['status']})")
        
        session.commit()
        print(f"\n🎉 用户优惠券数据插入完成!")
        print(f"   新增: {inserted_count} 个")
        print(f"   跳过: {skipped_count} 个")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--clear-templates":
            clear_coupon_templates_data()
        elif sys.argv[1] == "--clear-coupons":
            clear_user_coupons_data()
        elif sys.argv[1] == "--clear-all":
            clear_user_coupons_data()
            clear_coupon_templates_data()
        elif sys.argv[1] == "--summary-templates":
            show_coupon_templates_summary()
        elif sys.argv[1] == "--summary-coupons":
            show_user_coupons_summary()
        elif sys.argv[1] == "--summary":
            show_coupon_templates_summary()
            print()
            show_user_coupons_summary()
        elif sys.argv[1] == "--templates-only":
            insert_coupon_templates_data()
        elif sys.argv[1] == "--coupons-only":
            insert_user_coupons_data()
        else:
            print("用法: python initial_coupon_data.py [--clear-templates|--clear-coupons|--clear-all|--summary-templates|--summary-coupons|--summary|--templates-only|--coupons-only]")
    else:
        insert_coupon_templates_data()
        print()
        insert_user_coupons_data()
