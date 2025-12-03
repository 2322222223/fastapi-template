"""
初始化积分商城数据
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any

from sqlmodel import Session, select

from app.core.db import engine
from app.models import (
    PointsProductCategory,
    PointsProduct,
    PointsProductCategoryType,
    PointsProductLabel
)


def load_points_mall_data() -> Dict[str, Any]:
    """加载积分商城数据"""
    data_file = os.path.join(os.path.dirname(__file__), "data", "points_mall_data.json")
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data[0] if data else {}


def insert_points_mall_data():
    """插入积分商城数据"""
    data = load_points_mall_data()
    
    if not data:
        print("❌ 未找到积分商城数据")
        return
    
    with Session(engine) as session:
        # 创建分类映射（按名称）
        category_map = {}
        
        # 先插入分类
        if "categories" in data:
            categories_data = data["categories"]
            inserted_categories = 0
            skipped_categories = 0
            
            for category_data in categories_data:
                # 检查是否已存在相同名称的分类
                existing = session.exec(
                    select(PointsProductCategory).where(
                        PointsProductCategory.name == category_data["name"]
                    )
                ).first()
                
                if existing:
                    print(f"   ⏭️  跳过已存在的分类: {category_data['name']}")
                    skipped_categories += 1
                    category_map[category_data["category_type"]] = existing.id
                    continue
                
                # 创建分类
                category = PointsProductCategory(
                    name=category_data["name"],
                    category_type=PointsProductCategoryType(category_data["category_type"]),
                    icon_url=category_data.get("icon_url"),
                    sort_order=category_data.get("sort_order", 0),
                    is_active=category_data.get("is_active", True),
                    description=category_data.get("description")
                )
                
                session.add(category)
                session.flush()  # 获取ID
                category_map[category_data["category_type"]] = category.id
                inserted_categories += 1
                print(f"   ✅ 创建分类: {category_data['name']}")
            
            session.commit()
            print(f"\n📂 分类数据:")
            print(f"   新增: {inserted_categories} 个")
            print(f"   跳过: {skipped_categories} 个")
        
        # 再插入商品
        if "products" in data:
            products_data = data["products"]
            inserted_products = 0
            skipped_products = 0
            
            for product_data in products_data:
                # 检查是否已存在相同名称的商品
                existing = session.exec(
                    select(PointsProduct).where(
                        PointsProduct.name == product_data["name"]
                    )
                ).first()
                
                if existing:
                    print(f"   ⏭️  跳过已存在的商品: {product_data['name']}")
                    skipped_products += 1
                    continue
                
                # 获取分类ID
                category_type = product_data.get("category_type")
                if not category_type:
                    print(f"   ⚠️  跳过缺少分类的商品: {product_data['name']}")
                    skipped_products += 1
                    continue
                
                category_id = category_map.get(category_type)
                if not category_id:
                    print(f"   ⚠️  跳过找不到分类的商品: {product_data['name']} (分类: {category_type})")
                    skipped_products += 1
                    continue
                
                # 处理时间字段
                start_time = None
                end_time = None
                if product_data.get("start_time"):
                    start_time = datetime.fromisoformat(product_data["start_time"].replace("Z", "+00:00"))
                if product_data.get("end_time"):
                    end_time = datetime.fromisoformat(product_data["end_time"].replace("Z", "+00:00"))
                
                # 计算初始库存
                total_quantity = product_data.get("total_quantity", -1)
                exchanged_quantity = product_data.get("exchanged_quantity", 0)
                if total_quantity >= 0:
                    stock_quantity = total_quantity - exchanged_quantity
                else:
                    stock_quantity = -1
                
                # 处理标签字段
                label = None
                if product_data.get("label"):
                    try:
                        label = PointsProductLabel(product_data["label"])
                    except ValueError:
                        print(f"   ⚠️  无效的标签值: {product_data.get('label')}，将使用 None")
                
                # 创建商品
                product = PointsProduct(
                    name=product_data["name"],
                    description=product_data.get("description"),
                    image_url=product_data["image_url"],
                    images=product_data.get("images"),
                    category_id=category_id,
                    points_required=product_data["points_required"],
                    original_price=product_data.get("original_price"),
                    total_quantity=total_quantity,
                    exchanged_quantity=exchanged_quantity,
                    stock_quantity=stock_quantity,
                    is_active=product_data.get("is_active", True),
                    sort_order=product_data.get("sort_order", 0),
                    start_time=start_time,
                    end_time=end_time,
                    max_exchange_per_user=product_data.get("max_exchange_per_user", -1),
                    min_points_balance=product_data.get("min_points_balance", 0),
                    tags=product_data.get("tags"),
                    label=label,
                    detail_info=product_data.get("detail_info"),
                    usage_instructions=product_data.get("usage_instructions")
                )
                
                session.add(product)
                inserted_products += 1
                print(f"   ✅ 创建商品: {product_data['name']} ({product_data['points_required']}积分)")
            
            session.commit()
            print(f"\n🛍️  商品数据:")
            print(f"   新增: {inserted_products} 个")
            print(f"   跳过: {skipped_products} 个")
        
        print(f"\n🎉 积分商城数据插入完成!")


def show_points_mall_summary():
    """显示积分商城数据摘要"""
    with Session(engine) as session:
        # 分类统计
        categories = session.exec(select(PointsProductCategory)).all()
        print(f"📂 分类数据摘要:")
        print(f"   总数量: {len(categories)}")
        
        # 按类型分组统计
        type_stats = {}
        for category in categories:
            cat_type = category.category_type.value
            if cat_type not in type_stats:
                type_stats[cat_type] = {"count": 0, "active": 0}
            type_stats[cat_type]["count"] += 1
            if category.is_active:
                type_stats[cat_type]["active"] += 1
        
        type_names = {
            "data_package": "流量包",
            "membership_card": "会员卡",
            "coupon": "优惠券",
            "movie_ticket": "电影票",
            "physical_product": "实物商品"
        }
        
        for cat_type, stats in type_stats.items():
            type_name = type_names.get(cat_type, f"类型{cat_type}")
            print(f"   {type_name}: {stats['count']} 个 (激活: {stats['active']})")
        
        # 商品统计
        products = session.exec(select(PointsProduct)).all()
        print(f"\n🛍️  商品数据摘要:")
        print(f"   总数量: {len(products)}")
        
        # 按分类分组统计
        category_stats = {}
        for product in products:
            category = session.get(PointsProductCategory, product.category_id)
            cat_name = category.name if category else "未知"
            if cat_name not in category_stats:
                category_stats[cat_name] = {"count": 0, "active": 0, "total_points": 0}
            category_stats[cat_name]["count"] += 1
            if product.is_active:
                category_stats[cat_name]["active"] += 1
            category_stats[cat_name]["total_points"] += product.points_required
        
        for cat_name, stats in category_stats.items():
            avg_points = stats["total_points"] // stats["count"] if stats["count"] > 0 else 0
            print(f"   {cat_name}: {stats['count']} 个 (激活: {stats['active']}, 平均积分: {avg_points})")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--summary":
            show_points_mall_summary()
        else:
            print("用法: python initial_points_mall_data.py [--summary]")
    else:
        insert_points_mall_data()

