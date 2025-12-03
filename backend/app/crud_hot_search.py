
import uuid
from typing import List, Optional
from sqlmodel import Session, select, func
from app.models import HotSearch, HotSearchCreate, HotSearchUpdate

"""
热搜相关的CRUD操作
"""


def create(session: Session, obj_in: HotSearchCreate) -> HotSearch:
    """创建热搜"""
    db_obj = HotSearch.from_orm(obj_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get(session: Session, id: uuid.UUID) -> Optional[HotSearch]:
    """根据ID获取热搜"""
    return session.exec(select(HotSearch).where(HotSearch.id == id)).first()


def get_multi(
    session: Session, 
    skip: int = 0, 
    limit: int = 20
) -> List[HotSearch]:
    """获取热搜列表"""
    query = select(HotSearch)
    # 按ID排序
    query = query.order_by(HotSearch.id.desc())
    
    return session.exec(query.offset(skip).limit(limit)).all()


def update(session: Session, db_obj: HotSearch, obj_in: HotSearchUpdate) -> HotSearch:
    """更新热搜"""
    update_data = obj_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def delete(session: Session, id: uuid.UUID) -> bool:
    """删除热搜"""
    obj = session.get(HotSearch, id)
    if obj:
        session.delete(obj)
        session.commit()
        return True
    return False


def search_keywords(session: Session, keyword: str, skip: int = 0, limit: int = 20) -> List[HotSearch]:
    """搜索热搜关键词"""
    query = select(HotSearch).where(HotSearch.keyword.ilike(f"%{keyword}%"))
    query = query.order_by(HotSearch.id.desc())
    return session.exec(query.offset(skip).limit(limit)).all()


def get_total_count(session: Session) -> int:
    """获取总数"""
    return session.exec(select(func.count()).select_from(HotSearch)).one()


def get_by_keyword(session: Session, keyword: str) -> Optional[HotSearch]:
    """根据关键词获取热搜"""
    return session.exec(select(HotSearch).where(HotSearch.keyword == keyword)).first()


def create_if_not_exists(session: Session, obj_in: HotSearchCreate) -> HotSearch:
    """如果不存在则创建热搜"""
    existing = get_by_keyword(session, obj_in.keyword)
    if existing:
        return existing
    
    return create(session, obj_in)


def bulk_create(session: Session, objs_in: List[HotSearchCreate]) -> List[HotSearch]:
    """批量创建热搜"""
    created_objs = []
    for obj_in in objs_in:
        obj = create_if_not_exists(session, obj_in)
        created_objs.append(obj)
    
    return created_objs


def get_random(session: Session, limit: int = 10) -> List[HotSearch]:
    """获取随机热搜"""
    query = select(HotSearch).order_by(func.random()).limit(limit)
    return session.exec(query).all()


def get_latest(session: Session, limit: int = 10) -> List[HotSearch]:
    """获取最新热搜"""
    query = select(HotSearch).order_by(HotSearch.id.desc()).limit(limit)
    return session.exec(query).all()


def update_keyword(session: Session, id: uuid.UUID, new_keyword: str) -> Optional[HotSearch]:
    """更新热搜关键词"""
    obj = get(session, id)
    if not obj:
        return None
    
    obj.keyword = new_keyword
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_icon(session: Session, id: uuid.UUID, new_icon: str) -> Optional[HotSearch]:
    """更新热搜图标"""
    obj = get(session, id)
    if not obj:
        return None
    
    obj.icon = new_icon
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def exists(session: Session, keyword: str) -> bool:
    """检查关键词是否存在"""
    return get_by_keyword(session, keyword) is not None


def count_by_keyword_pattern(session: Session, pattern: str) -> int:
    """统计匹配模式的关键词数量"""
    query = select(func.count()).select_from(HotSearch).where(HotSearch.keyword.ilike(f"%{pattern}%"))
    return session.exec(query).one()


def get_keywords_starting_with(session: Session, prefix: str, limit: int = 20) -> List[HotSearch]:
    """获取以指定前缀开头的热搜"""
    query = select(HotSearch).where(HotSearch.keyword.ilike(f"{prefix}%")).limit(limit)
    return session.exec(query).all()


def get_keywords_ending_with(session: Session, suffix: str, limit: int = 20) -> List[HotSearch]:
    """获取以指定后缀结尾的热搜"""
    query = select(HotSearch).where(HotSearch.keyword.ilike(f"%{suffix}")).limit(limit)
    return session.exec(query).all()