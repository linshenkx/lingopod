from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from crud.task import task as task_crud
from schemas.task import TaskCreate, TaskResponse, TaskListResponse, TaskQueryParams, TaskUpdate
from models.user import User
from auth.dependencies import get_current_active_user, get_current_user
from db.session import get_db
from core.logging import log
import os
import threading

from models.enums import TaskProgress, TaskStatus
from services.task.task_service import execute_task
from services.file import FileService
from services.task import TaskService

router = APIRouter()

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # 创建任务
        task = task_crud.create(db=db, obj_in=task_in, user=current_user)
        db.commit()  # 提交事务以保存任务
        
        # 启动后台任务处理
        threading.Thread(
            target=execute_task,
            args=(task.taskId, False),
            daemon=True
        ).start()
        
        return task
    except Exception as e:
        db.rollback()
        log.error(f"Failed to create task: error={str(e)}")
        log.error("Traceback:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动任务处理失败: {str(e)}"
        )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取任务详情"""
    task = task_crud.get(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 检查任务权限
    if task.user_id != current_user.id and not task.is_public and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No permission to access this task")
    
    return task

@router.get("", response_model=TaskListResponse)
async def list_tasks(
    params: TaskQueryParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取任务列表，支持分页和过滤"""
    
    tasks, total = task_crud.get_tasks(
        db,
        current_user_id=current_user.id,
        is_admin=current_user.is_admin,
        params=params
    )
    
    return {
        "total": total,
        "items": tasks
    }

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除任务"""
    task = task_crud.get(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 检查删除权限
    if task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No permission to delete this task")
    
    # 删除任务文件
    FileService.delete_task_directory(task_id)
    
    # 删除数据库记录
    task_crud.delete(db, task_id=task_id)
    
    return {"message": "Task deleted successfully"}

@router.get("/files/{task_id}/{level}/{lang}/{file_type}")
async def get_task_file(
    task_id: str,
    level: str,
    lang: str,
    file_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取任务相关文件（音频、字幕等）
    
    Args:
        task_id: 任务ID
        level: 难度等级(elementary/intermediate/advanced)
        lang: 语言(cn/en)
        file_type: 文件类型(audio/subtitle)
    """
    task = task_crud.get(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 检查访问权限
    if task.user_id != current_user.id and not task.is_public and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No permission to access this file")
    
    # 生成标准化的文件名
    filename = FileService.get_task_file_name(
        level=level,
        lang=lang,
        file_type=file_type,
        task_id=task_id
    )
    
    # 获取文件完整路径
    file_path = FileService.get_task_file_path(task_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    # 根据文件类型设置 media_type
    media_types = {
        "audio": "audio/mpeg",
        "subtitle": "application/x-subrip",
    }
    media_type = media_types.get(file_type, "text/plain")
    
    return FileResponse(file_path, media_type=media_type)

@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """重试失败的任务"""
    task = task_crud.get(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 检查任务权限
    if task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No permission to retry this task")
    
    # 检查任务是否处于失败状态
    if task.status != TaskStatus.FAILED.value:
        raise HTTPException(status_code=400, detail="Only failed tasks can be retried")
    
    # 重置任务状态为处理中
    task.status = TaskStatus.PROCESSING.value
    task.progress = TaskProgress.WAITING.value
    db.commit()
    
    # 启动重试处理
    TaskService.retry_task(task)
    
    return {"message": "Task retry started"}

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新任务信息"""
    task = task_crud.get(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 检查更新权限
    if task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No permission to update this task")
    
    # 只更新允许的字段
    update_data = TaskUpdate(
        title=task_update.title if task_update.title is not None else task.title,
        is_public=task_update.is_public if task_update.is_public is not None else task.is_public,
        style_params=task_update.style_params if task_update.style_params is not None else task.style_params
    )
    
    updated_task = task_crud.update(db, db_obj=task, obj_in=update_data)
    return updated_task