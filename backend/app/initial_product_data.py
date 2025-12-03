#!/usr/bin/env python3
"""
初始化商品数据脚本
为每个店铺创建不同的商品数据（带查重机制）
"""

import json
import re
import uuid
from typing import List, Dict, Any

from sqlmodel import Session, select, func

from app.core.db import engine
from app.models import Product, ProductCreate, Store


def load_products_data() -> List[Dict[str, Any]]:
    """从JSON文件加载商品数据配置"""
    import os
    products_data_file = os.path.join(os.path.dirname(__file__), "data", "products_data.json")
    
    try:
        with open(products_data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 商品数据文件未找到: {products_data_file}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON文件格式错误: {e}")
        return []


def find_matching_store_config(store_name: str, store_configs: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """根据店铺名称找到匹配的商品配置"""
    for config in store_configs:
        pattern = config["store_name_pattern"]
        if re.search(pattern, store_name, re.IGNORECASE):
            return config
    return None


def create_sample_products() -> List[Product]:
    """创建示例商品数据（带查重机制）"""
    
    # 加载商品数据配置
    products_config = load_products_data()
    if not products_config:
        print("❌ 无法加载商品数据配置")
        return []
    
    with Session(engine) as session:
        # 检查是否已有商品数据
        existing_products = session.exec(select(Product)).all()
        if existing_products:
            print(f"✅ 发现已有 {len(existing_products)} 个商品，跳过创建")
            print("💡 如需重新创建，请先清空商品表")
            return existing_products
        
        # 获取所有店铺
        stores = session.exec(select(Store)).all()
        if not stores:
            print("❌ 没有找到店铺，请先创建店铺数据")
            return []
        
        print(f"🏪 找到 {len(stores)} 个店铺")
        
        total_created = 0
        products_data = []
        
        # 为每个店铺创建商品
        for store in stores:
            # 查找匹配的商品配置
            store_config = find_matching_store_config(store.name, products_config)
            
            if store_config:
                print(f"📦 为店铺 '{store.name}' 创建 {len(store_config['products'])} 个商品")
                
                for product_data in store_config["products"]:
                    # 创建ProductCreate对象
                    product_create = ProductCreate(
                        title=product_data["title"],
                        subtitle=product_data["subtitle"],
                        price=product_data["price"],
                        original_price=product_data["original_price"],
                        discount=product_data["discount"],
                        image_url=product_data["image_url"],
                        tag=product_data["tag"],
                        sales_count=product_data["sales_count"],
                        category=product_data["category"],
                        member_price=product_data.get("member_price"),
                        coupon_saved=product_data.get("coupon_saved"),
                        total_saved=product_data.get("total_saved"),
                        store_id=store.id
                    )
                    
                    products_data.append(product_create)
                    total_created += 1
            else:
                print(f"⚠️  店铺 '{store.name}' 没有找到匹配的商品配置")
        
        if products_data:
            # 批量插入商品
            for product_data in products_data:
                product = Product.from_orm(product_data)
                session.add(product)
            
            session.commit()
            print(f"✅ 成功创建 {total_created} 个商品")
        else:
            print("⚠️  没有创建任何商品")
        
        return session.exec(select(Product)).all()


def clear_products_data() -> bool:
    """清空所有商品数据（谨慎使用）"""
    with Session(engine) as session:
        try:
            # 获取商品总数
            total_count = session.exec(select(func.count(Product.id))).one()
            
            if total_count == 0:
                print("ℹ️  商品表已经是空的")
                return True
            
            # 删除所有商品
            session.exec(select(Product)).all()
            session.query(Product).delete()
            session.commit()
            
            print(f"🗑️  成功清空 {total_count} 个商品")
            return True
            
        except Exception as e:
            print(f"❌ 清空商品数据失败: {e}")
            session.rollback()
            return False


def show_products_summary() -> None:
    """显示商品数据摘要"""
    with Session(engine) as session:
        # 统计商品总数
        total_products = session.exec(select(func.count(Product.id))).one()
        
        if total_products == 0:
            print("📊 商品数据摘要: 暂无商品")
            return
        
        # 按店铺统计
        stores_with_products = session.exec(
            select(Store.name, func.count(Product.id))
            .join(Product)
            .group_by(Store.name)
        ).all()
        
        print(f"📊 商品数据摘要: 总计 {total_products} 个商品")
        print("🏪 各店铺商品数量:")
        for store_name, count in stores_with_products:
            print(f"   {store_name}: {count} 个商品")
        
        # 按分类统计
        categories = session.exec(
            select(Product.category, func.count(Product.id))
            .group_by(Product.category)
        ).all()
        
        print("\n📂 各分类商品数量:")
        for category, count in categories:
            print(f"   {category}: {count} 个商品")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        print("🗑️  清空商品数据...")
        clear_products_data()
    elif len(sys.argv) > 1 and sys.argv[1] == "--summary":
        print("📊 显示商品数据摘要...")
        show_products_summary()
    else:
        print("🚀 开始创建商品数据...")
        products = create_sample_products()
        print(f"🎉 商品数据创建完成，共 {len(products)} 个商品")
        print("\n💡 使用说明:")
        print("   python app/initial_product_data.py          # 创建商品数据")
        print("   python app/initial_product_data.py --clear  # 清空商品数据")
        print("   python app/initial_product_data.py --summary # 显示数据摘要")
