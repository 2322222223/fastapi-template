"""
手机号认证相关的API路由
"""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import SessionDep
from app.core import security
from app.core.config import settings
from app.models import (
    Message, 
    Token, 
    UserPublic,
    PhoneLoginRequest,
    PhoneRegisterRequest,
    SendVerificationCodeRequest
)

router = APIRouter(tags=["phone-auth"])


@router.post("/send-verification-code")
def send_verification_code(
    session: SessionDep, request: SendVerificationCodeRequest
):
    """
    发送验证码到手机号（模拟实现）
    在实际项目中，这里应该调用短信服务发送真实的验证码
    """
    # 验证手机号格式
    phone = request.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="手机号不能为空")
    
    # 在真实项目中，这里应该：
    # 1. 验证手机号格式
    # 2. 生成随机验证码
    # 3. 存储验证码到缓存（Redis等）
    # 4. 调用短信服务发送验证码
    
    # 模拟实现：总是返回成功
    #return Message(message=f"验证码已发送到 {phone}，请使用固定验证码 22223 进行登录")
    return {"message": f"验证码已发送到 {phone}", "code": "222223"}




@router.post("/login")
def phone_login(
    session: SessionDep, login_request: PhoneLoginRequest
) -> Token:
    """
    使用手机号和验证码登录
    """
    phone = login_request.phone.strip()
    verification_code = login_request.verification_code.strip()
    
    if not phone or not verification_code:
        raise HTTPException(status_code=400, detail="手机号和验证码不能为空")
    
    # 验证验证码并获取用户
    user = crud.authenticate_by_phone(
        session=session, 
        phone=phone, 
        verification_code=verification_code
    )
    
    if not user:
        # 如果用户不存在且验证码正确，可以考虑自动注册
        if verification_code == "222223":
            raise HTTPException(
                status_code=404, 
                detail="用户不存在，请先注册。验证码正确，可以使用注册接口创建账户。"
            )
        else:
            raise HTTPException(status_code=400, detail="手机号或验证码错误")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户账户已被禁用")
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/register")
def phone_register(
    session: SessionDep, register_request: PhoneRegisterRequest
) -> Token:
    """
    使用手机号和验证码注册新用户
    """
    phone = register_request.phone.strip()
    verification_code = register_request.verification_code.strip()
    
    if not phone or not verification_code:
        raise HTTPException(status_code=400, detail="手机号和验证码不能为空")
    
    # 验证验证码
    if verification_code != "222223":
        raise HTTPException(status_code=400, detail="验证码错误")
    
    # 检查用户是否已存在
    existing_user = crud.get_user_by_phone(session=session, phone=phone)
    if existing_user:
        raise HTTPException(status_code=400, detail="该手机号已注册，请直接登录")
    
    # 创建新用户
    try:
        user = crud.create_user_by_phone(
            session=session,
            phone=phone,
            full_name=register_request.full_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败：{str(e)}")
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/login-or-register")
def phone_login_or_register(
    session: SessionDep, request: PhoneLoginRequest
) -> Token:
    """
    手机号登录或注册（一体化接口）
    如果用户存在则登录，不存在则自动注册
    """
    phone = request.phone.strip()
    verification_code = request.verification_code.strip()
    
    if not phone or not verification_code:
        raise HTTPException(status_code=400, detail="手机号和验证码不能为空")
    
    # 验证验证码
    if verification_code != "222223":
        raise HTTPException(status_code=400, detail="验证码错误")
    
    # 尝试找到现有用户
    user = crud.get_user_by_phone(session=session, phone=phone)
    
    if not user:
        # 用户不存在，自动注册
        try:
            user = crud.create_user_by_phone(session=session, phone=phone)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"自动注册失败：{str(e)}")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户账户已被禁用")
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )
