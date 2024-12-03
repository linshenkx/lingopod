from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from models.user import User
from models.task import Task
from auth.dependencies import get_admin_user, get_current_active_user
from db.session import get_db
import os
import shutil
from core.config import settings
from schemas.user import UserResponse, UserListResponse, UserStatusUpdate
from typing import List
from sqlalchemy import and_
from schemas.user import UserUpdate
from schemas.user import PasswordUpdate
from utils.time_utils import TimeUtil
from auth.utils import verify_password, get_password_hash

router = APIRouter()

@router.get("/health", status_code=200)
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "message": "服务正常运行"}

@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """删除用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    
    # 删除用户相关的任务及其文件夹
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    for task in tasks:
        task_dir = os.path.join(settings.TASK_DIR, task.taskId)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
        db.delete(task)
    
    # 删除用户
    db.delete(user)
    db.commit()
    return {"message": "用户删除成功"}

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    return user 

@router.get("/", response_model=UserListResponse)
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    username: str = None,
    is_active: bool = None,
    start_date: int = None,
    end_date: int = None
):
    """获取用户列表，支持分页和过滤"""
    # 构建查询条件
    query = db.query(User)
    
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if start_date:
        query = query.filter(User.created_at >= start_date)
    if end_date:
        query = query.filter(User.created_at <= end_date)
    
    # 获取总数
    total = query.count()
    
    # 获取分页数据
    users = query.offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "items": users
    }

@router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    status_update: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """禁用或启用用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    
    user.is_active = status_update.is_active
    db.commit()
    db.refresh(user)
    return user

@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新当前用户信息"""
    # 更新用户信息
    if user_update.nickname is not None:
        current_user.nickname = user_update.nickname
    if user_update.email is not None:
        current_user.email = user_update.email
    if user_update.tts_voice is not None:
        current_user.tts_voice = user_update.tts_voice
    if user_update.tts_rate is not None:
        current_user.tts_rate = user_update.tts_rate
        
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/me/password", status_code=200)
async def update_password(
    password_update: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """修改当前用户密码"""
    # 验证旧密码
    if not verify_password(password_update.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新密码
    current_user.hashed_password = get_password_hash(password_update.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}