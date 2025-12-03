import json
import logging
from sqlmodel import Session, select
from app.core.db import engine
from app.models import HotSearch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_hot_search_data(session: Session) -> None:
    """创建热搜初始数据"""
    # 检查是否已有热搜数据
    existing_hot_search = session.exec(select(HotSearch)).first()
    if existing_hot_search:
        logger.info("热搜数据已存在，跳过初始化")
        return
    
    # 从JSON文件加载热搜数据
    import os
    hot_search_data_file = os.path.join(os.path.dirname(__file__), "data", "hot_search_data.json")
    
    try:
        with open(hot_search_data_file, 'r', encoding='utf-8') as f:
            hot_search_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"热搜数据文件未找到: {hot_search_data_file}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"JSON数据解析错误: {e}")
        return
    
    # 插入热搜数据
    for hot_search_item in hot_search_data:
        hot_search = HotSearch(**hot_search_item)
        session.add(hot_search)
    
    session.commit()
    logger.info(f"成功创建了 {len(hot_search_data)} 条热搜数据")


if __name__ == "__main__":
    logger.info("开始创建热搜数据...")
    with Session(engine) as session:
        create_hot_search_data(session)
    logger.info("热搜数据创建完成!")