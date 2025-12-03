#!/usr/bin/env python3
"""
初始化商品详情数据脚本
为每个商品创建对应的详情数据（带查重机制）
"""

import json
import os
import uuid
from typing import List, Dict, Any

from sqlmodel import Session, select, func

from app.core.db import engine
from app.models import Product, ProductDetail, ProductDetailCreate


def load_product_details_data() -> List[Dict[str, Any]]:
    """从JSON文件加载商品详情数据配置"""
    product_details_file = os.path.join(os.path.dirname(__file__), "data", "product_details_data.json")
    
    try:
        with open(product_details_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 商品详情数据文件未找到: {product_details_file}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON文件格式错误: {e}")
        return []


def create_sample_product_details() -> List[ProductDetail]:
    """创建示例商品详情数据（带查重机制）"""
    
    # 加载商品详情数据配置
    details_config = load_product_details_data()
    if not details_config:
        print("❌ 无法加载商品详情数据配置")
        return []
    
    with Session(engine) as session:
        # 检查是否已有商品详情数据
        existing_details = session.exec(select(ProductDetail)).all()
        if existing_details:
            print(f"✅ 发现已有 {len(existing_details)} 个商品详情，跳过创建")
            print("💡 如需重新创建，请先清空商品详情表")
            return existing_details
        
        # 获取所有商品
        products = session.exec(select(Product)).all()
        if not products:
            print("❌ 没有找到商品，请先创建商品数据")
            return []
        
        print(f"📦 找到 {len(products)} 个商品")
        
        total_created = 0
        details_data = []
        
        # 为每个商品创建详情（按顺序匹配）
        for i, product in enumerate(products):
            if i < len(details_config):
                detail_config = details_config[i]
                
                print(f"📝 为商品 '{product.title}' 创建详情")
                
                # 创建ProductDetailCreate对象
                detail_create = ProductDetailCreate(
                    name=detail_config["name"],
                    description=detail_config["description"],
                    short_description=detail_config["short_description"],
                    sku=detail_config["sku"],
                    price=detail_config["price"],
                    sale_price=detail_config.get("sale_price"),
                    stock_quantity=detail_config["stock_quantity"],
                    is_in_stock=detail_config["is_in_stock"],
                    category_id=detail_config.get("category_id"),
                    main_image_url=detail_config["main_image_url"],
                    gallery_image_urls=detail_config["gallery_image_urls"],
                    tags=detail_config["tags"],
                    status=detail_config["status"],
                    attributes=detail_config["attributes"],
                    variants=detail_config["variants"],
                    average_rating=detail_config["average_rating"],
                    review_count=detail_config["review_count"],
                    gift_data_package=detail_config.get("gift_data_package"),
                    gift_coupon=detail_config.get("gift_coupon"),
                    gift_voice_package=detail_config.get("gift_voice_package"),
                    gift_membership=detail_config.get("gift_membership"),
                    product_id=product.id
                )
                
                details_data.append(detail_create)
                total_created += 1
            else:
                print(f"⚠️  商品 '{product.title}' 没有对应的详情配置")
        
        if details_data:
            # 批量插入商品详情
            for detail_data in details_data:
                detail = ProductDetail.model_validate(detail_data)
                session.add(detail)
            
            session.commit()
            print(f"✅ 成功创建 {total_created} 个商品详情")
        else:
            print("⚠️  没有创建任何商品详情")
        
        return session.exec(select(ProductDetail)).all()


def clear_product_details_data() -> bool:
    """清空所有商品详情数据（谨慎使用）"""
    with Session(engine) as session:
        try:
            # 获取商品详情总数
            total_count = session.exec(select(func.count(ProductDetail.id))).one()
            
            if total_count == 0:
                print("ℹ️  商品详情表已经是空的")
                return True
            
            # 删除所有商品详情
            details = session.exec(select(ProductDetail)).all()
            for detail in details:
                session.delete(detail)
            session.commit()
            
            print(f"🗑️  成功清空 {total_count} 个商品详情")
            return True
            
        except Exception as e:
            print(f"❌ 清空商品详情数据失败: {e}")
            session.rollback()
            return False


def show_product_details_summary() -> None:
    """显示商品详情数据摘要"""
    with Session(engine) as session:
        # 统计商品详情总数
        total_details = session.exec(select(func.count(ProductDetail.id))).one()
        
        if total_details == 0:
            print("📊 商品详情数据摘要: 暂无商品详情")
            return
        
        print(f"📊 商品详情数据摘要: 总计 {total_details} 个商品详情")
        
        # 按状态统计
        published_count = session.exec(
            select(func.count(ProductDetail.id)).where(ProductDetail.status == "published")
        ).one()
        
        print(f"📈 已发布商品详情: {published_count} 个")
        
        # 统计赠品类型
        gift_stats = {
            "流量包": session.exec(select(func.count(ProductDetail.id)).where(ProductDetail.gift_data_package.isnot(None))).one(),
            "优惠券": session.exec(select(func.count(ProductDetail.id)).where(ProductDetail.gift_coupon.isnot(None))).one(),
            "语音包": session.exec(select(func.count(ProductDetail.id)).where(ProductDetail.gift_voice_package.isnot(None))).one(),
            "会员": session.exec(select(func.count(ProductDetail.id)).where(ProductDetail.gift_membership.isnot(None))).one(),
        }
        
        print("\n🎁 赠品统计:")
        for gift_type, count in gift_stats.items():
            if count > 0:
                print(f"   {gift_type}: {count} 个商品")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        print("🗑️  清空商品详情数据...")
        clear_product_details_data()
    elif len(sys.argv) > 1 and sys.argv[1] == "--summary":
        print("📊 显示商品详情数据摘要...")
        show_product_details_summary()
    else:
        print("🚀 开始创建商品详情数据...")
        details = create_sample_product_details()
        print(f"🎉 商品详情数据创建完成，共 {len(details)} 个详情")
        print("\n💡 使用说明:")
        print("   python app/initial_product_detail_data.py          # 创建商品详情数据")
        print("   python app/initial_product_detail_data.py --clear  # 清空商品详情数据")
        print("   python app/initial_product_detail_data.py --summary # 显示数据摘要")
