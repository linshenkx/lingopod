from core.logging import log
from typing import Optional

import sqlalchemy
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from models.enums import TaskProgress, TaskStatus
from models.task import Task
from utils.time_utils import TimeUtil
from services.file import FileService


class ProgressTracker:
    def __init__(self, task: Task, db: Session, total_steps: int):
        self.task = task
        self.db = db
        self.total_steps = total_steps
        self.db.add(self.task)
        
    def update_progress(
        self,
        step_index: int,
        step_name: str,
        progress: int = 0,
        message: Optional[str] = None
    ):
        """更新任务进度"""
        log.info(f"Updating progress for task {self.task.taskId}: step={step_name}, index={step_index}, progress={progress}")
        
        progress_status = (
            TaskProgress.COMPLETED.value if progress == 100
            else TaskProgress.PROCESSING.value
        )
        
        progress_message = ""
        if message:
            progress_message += f"{message}"
            
        self._update_task_status(
            status=TaskStatus.PROCESSING.value,
            progress=progress_status,
            progress_message=progress_message,
            current_step=step_name,
            current_step_index=step_index,
            step_progress=progress
        )
    
    def _update_task_status(
        self,
        status: str,
        progress: str,
        progress_message: str,
        current_step: str,
        current_step_index: int,
        step_progress: int,
        error_message: Optional[str] = None
    ):
        """更新任务状态"""
        log.info(f"Updating task {self.task.taskId} status: status={status}, progress={progress}, message={progress_message}")
        
        try:
            self.db.refresh(self.task)
        except Exception as e:
            log.error(f"Failed to refresh task {self.task.taskId}: {str(e)}")
            raise
        
        if error_message:
            self.task.status = TaskStatus.FAILED.value
            self.task.progress = TaskProgress.FAILED.value
            self.task.progress_message = error_message
        else:
            self.task.status = status
            self.task.progress = progress
            self.task.progress_message = progress_message
            
        self.task.updatedAt = TimeUtil.now_ms()
        self.task.current_step = current_step
        self.task.current_step_index = current_step_index
        self.task.step_progress = step_progress
        
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise Exception(f"更新任务状态失败: {str(e)}")
    
    def update_error(self, error_msg: str, stack_trace: Optional[str] = None):
        """处理错误进度更新"""
        task_id = self.task.taskId  # 预先保存taskId
        try:
            error_message = error_msg
            if stack_trace:
                error_message += f"\n堆栈信息:\n{stack_trace}"
            
            self._update_task_status(
                status=TaskStatus.FAILED.value,
                progress=TaskProgress.FAILED.value,
                progress_message="任务执行失败",
                current_step=self.task.current_step,
                current_step_index=self.task.current_step_index,
                step_progress=0,
                error_message=error_message
            )
        except (sqlalchemy.orm.exc.ObjectDeletedError, sqlalchemy.exc.InvalidRequestError) as e:
            # 任务已被删除，记录日志
            log.warning(f"Cannot update error status, task has been deleted: {task_id}")
    


    def update_files(self, level: str, lang: str, file_type: str):
        """更新任务文件结构
        
        Args:
            level: 难度等级(elementary/intermediate/advanced)
            lang: 语言(cn/en)
            file_type: 文件类型(audio/subtitle)
        """
        try:
            self.db.refresh(self.task)
            
            # 确保 files 字典存在并且是可变的
            if not self.task.files:
                self.task.files = {}
            
            # 创建嵌套结构
            if level not in self.task.files:
                self.task.files[level] = {}
            if lang not in self.task.files[level]:
                self.task.files[level][lang] = {}
            
            # 使用 FileService 生成文件名并更新文件结构
            filename = FileService.update_task_files(
                task_id=self.task.taskId,
                level=level,
                lang=lang,
                file_type=file_type
            )
            
            # 更新文件信息
            self.task.files[level][lang][file_type] = filename
            
            # 标记 files 字段为已修改
            flag_modified(self.task, "files")
            
            # 提交更改
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"更新任务文件结构失败: {str(e)}")