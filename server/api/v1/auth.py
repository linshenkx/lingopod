from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from auth.utils import verify_password, get_password_hash, create_access_token
from db.session import get_db
from core.config import settings
from schemas.user import UserCreate, UserResponse
from models.user import User
from auth.dependencies import get_current_active_user
from utils.time_utils import TimeUtil

router = APIRouter()

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # 特殊处理test用户
    if (settings.TEST_USER_ENABLED and 
        form_data.username == settings.TEST_USERNAME and 
        form_data.password == settings.TEST_PASSWORD):
        
        # 获取或创建test用户
        user = db.query(User).filter(User.username == settings.TEST_USERNAME).first()
        if not user:
            # 创建test用户
            user = User(
                username=settings.TEST_USERNAME,
                hashed_password=get_password_hash(settings.TEST_PASSWORD),
                nickname="Test User",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户已被禁用"
            )
        
        # 更新最近登录时间
        user.last_login = TimeUtil.now_ms()
        db.commit()
    
    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/register", status_code=201)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if not settings.ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="注册功能已关闭"
        )
    
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(
        User.username == user_data.username
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    user = User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        nickname=user_data.nickname or user_data.username
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"username": user.username, "nickname": user.nickname}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前登录用户信息"""
    return current_user
