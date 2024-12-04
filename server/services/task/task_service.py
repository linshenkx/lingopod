import threading
import os
import shutil
from models.task import Task
from core.config import settings
from db.session import get_db
from models.enums import TaskProgress, TaskStatus
from utils.time_utils import TimeUtil
from services.task.processor import TaskProcessor
from utils.decorators import error_handler
from services.file import FileService
from core.logging import log
import sqlalchemy.orm.exc
import sqlalchemy.exc

@error_handler
def execute_task(task: Task, is_retry: bool = False):
    """执行任务的入口函数"""
    task_id = task.taskId  # 预先保存taskId
    db = next(get_db())
    try:
        processor = TaskProcessor(task, db, is_retry)
        try:
            processor.process_task()
        except (sqlalchemy.orm.exc.ObjectDeletedError, sqlalchemy.exc.InvalidRequestError) as e:
            # 任务已被删除，记录日志并优雅退出
            log.warning(f"Task has been deleted during processing: {task_id}")
            return
        except Exception as e:
            # 其他错误继续抛出
            raise
    finally:
        db.close()
        
class TaskService:
    @staticmethod
    def retry_task(task: Task):
        """重试失败的任务"""
        threading.Thread(target=execute_task, args=(task, True)).start()

    @staticmethod
    def start_processing(task: Task):
        """启动任务处理线程"""
        # 先更新状态
        task.status = TaskStatus.PROCESSING.value
        task.progress = TaskProgress.PROCESSING.value
        task.progress_message = "任务开始处理"
        db = next(get_db())
        try:
            db.commit()
        finally:
            db.close()
        
        # 然后启动处理线程
        threading.Thread(target=execute_task, args=(task, False)).start()

    @staticmethod
    def check_incomplete_tasks(db):
        """检查未完成的任务并清理文件"""
        try:
            # 1. 将所有未完成任务标记为失败
            incomplete_tasks = (
                db.query(Task)
                .filter(Task.status.in_(['pending', 'processing']))
                .all()
            )
            
            for task in incomplete_tasks:
                db.refresh(task)  # 刷新任务对象
                task.status = TaskStatus.FAILED.value
                task.progress = TaskProgress.FAILED.value
                task.progress_message = "应用重启时任务未完成"
                task.updatedAt = TimeUtil.now_ms()
            
            db.commit()
        except Exception as e:
            db.rollback()
            raise Exception(f"更新未完成任务状态失败: {str(e)}")
