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
from sqlalchemy.orm import Session
import time

@error_handler
def execute_task(task_id: str, is_retry: bool = False, db_session = None):
    """执行任务的入口函数
    
    Args:
        task_id: 任务ID
        is_retry: 是否为重试执行
        db_session: 可选的数据库会话，用于测试环境
    """
    log.info(f"Starting task execution: task_id={task_id}, is_retry={is_retry}")
    
    if db_session:
        db = db_session
        should_close = False
    else:
        db = next(get_db())
        should_close = True
        
    try:
        # 在会话中获取任务对象
        task = db.query(Task).filter(Task.taskId == task_id).first()
        if not task:
            log.error(f"Task not found in execute_task: {task_id}")
            return

        # 确保任务状态正确
        if task.status != TaskStatus.PROCESSING.value:
            task.status = TaskStatus.PROCESSING.value
            task.progress = TaskProgress.PROCESSING.value
            db.commit()
            db.refresh(task)
            
        log.info(f"Task found, current status: {task.status}, progress: {task.progress}")
        processor = TaskProcessor(task, db, is_retry)
        try:
            processor.process_task()
            log.info(f"Task processing completed successfully: {task_id}")
        except (sqlalchemy.orm.exc.ObjectDeletedError, sqlalchemy.exc.InvalidRequestError) as e:
            # 任务已被删除，记录日志并优雅退出
            log.warning(f"Task has been deleted during processing: {task_id}, error: {str(e)}")
            return
        except Exception as e:
            # 记录详细错误信息
            log.error(f"Error processing task: {task_id}, error: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                log.error(f"Traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise
    finally:
        if should_close and db:
            db.close()
            log.info(f"Task execution finished, database session closed: {task_id}")

class TaskService:
    @staticmethod
    def retry_task(task: Task):
        """重试失败的任务"""
        threading.Thread(target=execute_task, args=(task.taskId, True)).start()

    @staticmethod
    def start_processing(task: Task):
        """启动任务处理线程"""
        task_id = task.taskId  # 保存任务ID
        db = None
        
        try:
            # 获取新的会话
            db = next(get_db())
            # 在当前会话中获取新的任务对象
            current_task = db.query(Task).filter(Task.taskId == task_id).first()
            if not current_task:
                log.error(f"Task not found in start_processing: {task_id}")
                raise Exception(f"Task not found: {task_id}")
            
            # 检查任务状态
            if current_task.status not in [TaskStatus.PENDING.value, TaskStatus.FAILED.value]:
                log.warning(f"Task is not in a valid state for processing: {task_id}, current status: {current_task.status}")
                return
                
            # 更新任务状态
            current_task.status = TaskStatus.PROCESSING.value
            current_task.progress = TaskProgress.PROCESSING.value
            current_task.progress_message = "任务开始处理"
            current_task.error = None  # 清除之前的错误信息
            db.commit()
            db.refresh(current_task)
            
            # 在确认状态更新成功后立即启动处理线程
            log.info(f"Starting task processing thread: {task_id}")
            processing_thread = threading.Thread(target=execute_task, args=(task_id, False))
            processing_thread.daemon = True  # 设置为守护线程
            processing_thread.start()
            log.info(f"Task processing thread started: {task_id}")
            
        except Exception as e:
            if db:
                db.rollback()
            log.error(f"Failed to start task processing: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                log.error(f"Traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise
        finally:
            if db:
                db.close()
                log.info(f"Task processing start finished, database session closed: {task_id}")

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

    @classmethod
    def start_processing_with_task(cls, task: Task, db: Session):
        """使用已有任务对象启动处理"""
        try:
            # 检查任务状态
            if task.status not in [TaskStatus.PENDING.value, TaskStatus.FAILED.value]:
                log.warning(f"Task is not in a valid state for processing: {task.taskId}, current status: {task.status}")
                return
                
            # 更新任务状态
            task.status = TaskStatus.PROCESSING.value
            task.progress = TaskProgress.PROCESSING.value
            task.progress_message = "任务开始处理"
            task.error = None
            db.commit()
            db.refresh(task)
            
            # 确保任务目录存在
            task_dir = os.path.join(settings.TASK_DIR, task.taskId)
            os.makedirs(task_dir, exist_ok=True)
            
            # 启动处理线程
            log.info(f"Starting task processing thread: {task.taskId}")
            time.sleep(0.1)  # Add a small delay to ensure transaction is committed
            processing_thread = threading.Thread(target=execute_task, args=(task.taskId, False))
            processing_thread.daemon = True
            processing_thread.start()
            log.info(f"Task processing thread started: {task.taskId}")
            
        except Exception as e:
            db.rollback()
            log.error(f"Failed to start task processing: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                log.error(f"Traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
            raise
