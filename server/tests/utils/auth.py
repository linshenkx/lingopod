from datetime import datetime, timedelta
from typing import Optional

from jose import jwt

from core.config import settings

def create_test_token(
    username: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """创建测试用的JWT令牌"""
    to_encode = {"sub": username}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt 