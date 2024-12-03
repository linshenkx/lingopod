from typing import Optional

from sqlalchemy.orm import Session

from models.enums import TaskProgress, TaskStatus
from models.task import Task
from utils.time_utils import TimeUtil


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
        self.db.refresh(self.task)
        
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
