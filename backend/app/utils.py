import io
import logging
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import emails  # type: ignore
import jwt
from fastapi import UploadFile, HTTPException
from jinja2 import Template
from jwt.exceptions import InvalidTokenError

from app.core import security
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f"send email result: {response}")


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Password recovery for user {email}"
    link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.FRONTEND_HOST,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None


def generate_pickup_code() -> str:
    """生成9位数字取餐码"""
    # 生成9位数字，确保第一位不为0
    first_digit = random.randint(1, 9)
    remaining_digits = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{first_digit}{remaining_digits}"


def generate_invite_code(length: int = 8) -> str:
    """
    生成用户邀请码
    
    Args:
        length: 邀请码长度，默认8位
        
    Returns:
        生成的邀请码字符串
        
    Note:
        - 使用大写字母和数字，避免容易混淆的字符（O, 0, I, 1）
        - 确保全局唯一性
    """
    # 定义字符集：大写字母和数字，排除容易混淆的字符
    charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    
    # 生成指定长度的邀请码
    invite_code = ''.join(random.choices(charset, k=length))
    
    return invite_code


def validate_image_file(file: UploadFile) -> None:
    """
    验证上传的图片文件
    
    Args:
        file: FastAPI UploadFile 对象
        
    Raises:
        HTTPException: 如果文件不符合要求
    """
    # 检查文件扩展名
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    # 检查文件大小
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置到文件开头
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制。最大允许: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )


async def save_avatar_file(file: UploadFile, user_id: uuid.UUID) -> str:
    """
    保存用户头像文件
    
    Args:
        file: FastAPI UploadFile 对象
        user_id: 用户ID
        
    Returns:
        保存后的文件相对路径（用于生成URL）
        
    Raises:
        HTTPException: 如果保存失败
    """
    try:
        # 验证文件
        validate_image_file(file)
        
        # 确保上传目录存在
        upload_dir = Path(settings.AVATAR_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一文件名
        file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = upload_dir / filename
        
        # 读取文件内容
        file_content = await file.read()
        
        # 验证并处理图片（使用PIL，延迟导入）
        try:
            from PIL import Image  # 延迟导入，避免在模块导入时就需要 pillow
            
            image = Image.open(io.BytesIO(file_content))
            # 转换为RGB模式（处理RGBA等格式）
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # 调整图片大小（可选：限制最大尺寸）
            max_size = (800, 800)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 保存图片
            image.save(file_path, "JPEG", quality=85, optimize=True)
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="图片处理功能需要安装 pillow 库，请运行: uv sync"
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"图片处理失败: {str(e)}"
            )
        
        # 返回相对路径（用于生成URL）
        return f"{settings.AVATAR_UPLOAD_DIR}/{filename}"
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存头像文件失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"保存头像文件失败: {str(e)}"
        )


def delete_avatar_file(avatar_url: str) -> None:
    """
    删除用户头像文件
    
    Args:
        avatar_url: 头像URL或文件路径
    """
    try:
        if avatar_url:
            # 如果是URL，提取路径部分
            if avatar_url.startswith("http"):
                # 从URL中提取路径
                from urllib.parse import urlparse
                parsed = urlparse(avatar_url)
                file_path = Path(parsed.path.lstrip("/"))
            else:
                file_path = Path(avatar_url)
            
            # 确保文件在允许的目录内（安全检查）
            if str(file_path).startswith(settings.AVATAR_UPLOAD_DIR):
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"删除头像文件: {file_path}")
    except Exception as e:
        logger.error(f"删除头像文件失败: {str(e)}")
