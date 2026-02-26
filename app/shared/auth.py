from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from loguru import logger

from config.settings import get_settings


# API Key Header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT access token

    Args:
        data: 要编码的数据（通常包含 sub 字段）
        expires_delta: 过期时间增量，默认从配置读取

    Returns:
        JWT token 字符串
    """
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    验证 JWT token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的 payload

    Raises:
        HTTPException: token 无效或过期
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT 验证失败: {e}")
        raise credentials_exception


async def api_key_auth(api_key: str = Security(api_key_header)) -> str:
    """
    API Key 验证中间件

    用法：
        @router.get("/protected")
        async def protected_route(api_key: str = Depends(api_key_auth)):
            ...

    Returns:
        验证通过的 API key

    Raises:
        HTTPException: API key 缺失或无效
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key",
        )

    settings = get_settings()

    # 验证 API key（这里简单对比，生产环境可对接数据库）
    if api_key != settings.llm_api_key:
        logger.warning("无效的 API Key 尝试")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的 API Key",
        )

    return api_key
