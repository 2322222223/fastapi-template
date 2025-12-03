import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, User, UserCreate, UserUpdate
from app.crud_invitation import generate_unique_invite_code


def create_user(*, session: Session, user_create: UserCreate) -> User:
    # 生成唯一邀请码
    invite_code = generate_unique_invite_code(session=session)
    
    db_obj = User.model_validate(
        user_create, update={
            "hashed_password": get_password_hash(user_create.password),
            "invite_code": invite_code
        }
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def get_user_by_phone(*, session: Session, phone: str) -> User | None:
    statement = select(User).where(User.phone == phone)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def authenticate_by_phone(*, session: Session, phone: str, verification_code: str) -> User | None:
    """使用手机号和验证码认证用户"""
    # 简单的固定验证码验证
    if verification_code != "22223":
        return None
    
    db_user = get_user_by_phone(session=session, phone=phone)
    return db_user


def create_user_by_phone(*, session: Session, phone: str, full_name: str | None = None) -> User:
    """使用手机号创建用户"""
    # 为手机号用户生成一个临时邮箱
    temp_email = f"{phone.replace('+', '').replace('-', '').replace(' ', '')}@herenow.com"
    
    # 生成唯一邀请码
    invite_code = generate_unique_invite_code(session=session)
    
    # 临时绕过密码哈希问题，使用固定哈希值
    temp_password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/4.4.4.4"
    
    db_obj = User(
        email=temp_email,
        phone=phone,
        full_name=full_name,
        hashed_password=temp_password_hash,  # 临时固定密码哈希
        is_active=True,
        is_superuser=False,
        invite_code=invite_code
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item
