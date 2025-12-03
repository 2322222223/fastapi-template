"""
初始化地区、商圈和商店数据
包含北京悠唐购物中心的真实假数据
"""
import uuid
import logging
from sqlmodel import Session, select
from app.core.db import engine
from app.models import Region, BusinessDistrict, Store
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_initial_data() -> None:
    """创建初始地区、商圈和商店数据"""
    with Session(engine) as session:
        # 智能检查：先查找北京地区
        beijing_region = session.exec(select(Region).where(Region.code == "BJ-001")).first()
        
        if not beijing_region:
            # 创建北京地区
            beijing_region = Region(
                name="北京市",
                code="BJ-001",
                country="中国",
                province="北京市",
                city="北京市"
            )
            session.add(beijing_region)
            session.commit()
            session.refresh(beijing_region)
            logger.info("创建北京地区")
        else:
            logger.info("北京地区已存在")
        
        # 查找悠唐购物中心
        youtang_mall = session.exec(
            select(BusinessDistrict).where(
                BusinessDistrict.name == "悠唐购物中心",
                BusinessDistrict.region_id == beijing_region.id
            )
        ).first()
        
        if not youtang_mall:
            # 创建悠唐购物中心
            youtang_mall = BusinessDistrict(
                name="悠唐购物中心",
                image_url="https://img.meituan.net/csc/95a183e5b48945e8e1da5dde7c060b11345320.jpg",
                rating=4.3,
                free_duration=120,  # 2小时免费停车
                ranking=8,
                address="北京市朝阳区三丰北里3号悠唐购物中心",
                distance="2.3km",
                region_id=beijing_region.id
            )
            session.add(youtang_mall)
            session.commit()
            session.refresh(youtang_mall)
            logger.info("创建悠唐购物中心")
        else:
            logger.info("悠唐购物中心已存在")
        
        # 插入商店数据（智能去重）
        insert_youtang_stores(session, youtang_mall)

        # 创建其他区域和商圈示例数据
        create_additional_sample_data(session)


def insert_youtang_stores(session: Session, youtang_mall: BusinessDistrict) -> None:
    """插入悠唐购物中心的商店数据（智能去重）"""
    # 从JSON文件加载商店数据
    import os
    stores_data_file = os.path.join(os.path.dirname(__file__), "data", "stores_data.json")
    
    try:
        with open(stores_data_file, 'r', encoding='utf-8') as f:
            stores_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"商店数据文件未找到: {stores_data_file}")
        stores_data = []
    except json.JSONDecodeError as e:
        logger.error(f"JSON数据解析错误: {e}")
        stores_data = []

    if not stores_data:
        logger.warning("没有找到商店数据")
        return

    # 获取悠唐购物中心现有商店名称
    existing_store_names = set()
    existing_stores = session.exec(
        select(Store.name).where(Store.business_district_id == youtang_mall.id)
    ).all()
    existing_store_names.update(existing_stores)
    
    # 插入不重复的商店数据
    inserted_count = 0
    skipped_count = 0
    
    for store_data in stores_data:
        store_name = store_data.get('name')
        
        if store_name in existing_store_names:
            skipped_count += 1
            logger.debug(f"跳过重复商店: {store_name}")
            continue
            
        # 插入新商店
        store = Store(
            business_district_id=youtang_mall.id,
            **store_data
        )
        session.add(store)
        existing_store_names.add(store_name)  # 避免同批次重复
        inserted_count += 1

    session.commit()
    logger.info(f"商店数据处理完成 - 新增: {inserted_count}个, 跳过重复: {skipped_count}个")


def create_additional_sample_data(session: Session) -> None:
    """创建其他示例数据"""
    
    # 检查上海地区是否存在
    shanghai_region = session.exec(select(Region).where(Region.code == "SH-001")).first()
    
    if not shanghai_region:
        # 创建上海地区
        shanghai_region = Region(
            name="上海市",
            code="SH-001",
            country="中国",
            province="上海市",
            city="上海市"
        )
        session.add(shanghai_region)
        session.commit()
        session.refresh(shanghai_region)
        logger.info("创建上海地区")
    else:
        logger.info("上海地区已存在")
    
    # 检查港汇恒隆广场是否存在
    ganghui_mall = session.exec(
        select(BusinessDistrict).where(
            BusinessDistrict.name == "港汇恒隆广场",
            BusinessDistrict.region_id == shanghai_region.id
        )
    ).first()
    
    if not ganghui_mall:
        # 创建上海港汇恒隆广场
        ganghui_mall = BusinessDistrict(
            name="港汇恒隆广场",
            image_url="https://img.meituan.net/csc/ganghui_plaza_cover.jpg",
            rating=4.5,
            free_duration=180,  # 3小时免费停车
            ranking=3,
            address="上海市徐汇区虹桥路1号港汇恒隆广场",
            distance="1.8km",
            region_id=shanghai_region.id
        )
        session.add(ganghui_mall)
        session.commit()
        session.refresh(ganghui_mall)
        logger.info("创建港汇恒隆广场")
    else:
        logger.info("港汇恒隆广场已存在")

    # 添加港汇恒隆的几个商店
    ganghui_stores = [
        {
            "name": "喜茶",
            "category": "咖啡茶饮",
            "rating": 4.6,
            "review_count": 2567,
            "price_range": "￥￥",
            "location": "港汇恒隆广场B1层",
            "floor": "B1",
            "image_url": "https://img.meituan.net/csc/heytea_cover.jpg",
            "tags": '["奶茶", "新式茶饮", "网红"]',
            "is_live": True,
            "has_delivery": True,
            "distance": "50m",
            "title": "喜茶(港汇恒隆店)",
            "sub_title": "芝芝莓莓限时特价",
            "sub_icon": "🍓",
            "type": 1,
            "business_district_id": ganghui_mall.id
        },
        {
            "name": "鼎泰丰",
            "category": "中餐",
            "rating": 4.8,
            "review_count": 3421,
            "price_range": "￥￥￥",
            "location": "港汇恒隆广场6层",
            "floor": "6F",
            "image_url": "https://img.meituan.net/csc/dingtaifeng_cover.jpg",
            "tags": '["小笼包", "台菜", "精致"]',
            "is_live": True,
            "has_delivery": False,
            "distance": "80m",
            "title": "鼎泰丰(港汇恒隆店)",
            "sub_title": "米其林推荐餐厅",
            "sub_icon": "⭐",
            "type": 2,
            "business_district_id": ganghui_mall.id
        }
    ]

    # 获取港汇恒隆现有商店名称（去重）
    existing_ganghui_names = set()
    existing_ganghui_stores = session.exec(
        select(Store.name).where(Store.business_district_id == ganghui_mall.id)
    ).all()
    existing_ganghui_names.update(existing_ganghui_stores)
    
    # 插入不重复的港汇恒隆商店
    ganghui_inserted = 0
    for store_data in ganghui_stores:
        store_name = store_data.get('name')
        if store_name not in existing_ganghui_names:
            store = Store(**store_data)
            session.add(store)
            existing_ganghui_names.add(store_name)
            ganghui_inserted += 1

    session.commit()
    logger.info(f"港汇恒隆商店数据 - 新增: {ganghui_inserted}个")


if __name__ == "__main__":
    logger.info("开始创建地区、商圈和商店数据...")
    create_initial_data()
    logger.info("地区、商圈和商店数据创建完成!")