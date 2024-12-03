from typing import List, Dict
from sqlalchemy.orm import Session
import os

from models.task import Task
from models.enums import TaskProgress, TaskStatus
from services.task.steps.audio import AudioStep
from services.task.steps.audio_merge import AudioMergeStep
from services.task.steps.content import ContentStep
from services.task.steps.dialogue import DialogueStep
from services.task.steps.subtitle import SubtitleStep
from services.task.steps.translation import TranslationStep
from services.task.utils.errors import TaskError
from .utils.context import ContextManager
from .utils.progress_tracker import ProgressTracker
from .steps.base import BaseStep
from core.logging import log
from core.config import settings

class TaskProcessor:
    """任务处理器"""
    
    def __init__(self, task: Task, db: Session, is_retry: bool = False):
        self.task = task
        self.db = db
        self.is_retry = is_retry
        self.temp_dir = os.path.join(settings.TASK_DIR, task.taskId)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.context_manager = ContextManager(task, self.temp_dir)
        self.steps = self._create_steps_without_tracker()
        self.progress_tracker = ProgressTracker(task, db, len(self.steps))
        self._update_steps_tracker()
        self.start_step = self._get_start_step(is_retry)
        
    def _create_steps_without_tracker(self) -> List[BaseStep]:
        """创建处理步骤列表(不包含progress_tracker)"""
        # 基础参数
        base_params = {
            "progress_tracker": None,  # 暂时为None
            "context_manager": self.context_manager
        }
        
        # 需要中英文处理的步骤类
        bilingual_steps = [
            (AudioStep, "音频生成"),
            (SubtitleStep, "字幕生成"), 
            (AudioMergeStep, "音频合并")
        ]
        
        steps = [
            ContentStep(**base_params),
            DialogueStep(**base_params),
            TranslationStep(**base_params)
        ]
        
        # 添加中英文步骤
        for step_class, _ in bilingual_steps:
            for lang in ["cn", "en"]:
                steps.append(step_class(lang, **base_params))
                
        return steps

    def _update_steps_tracker(self):
        """更新所有步骤的progress_tracker"""
        for step in self.steps:
            step.progress_tracker = self.progress_tracker

    def process_task(self):
        """处理任务"""
        try:
            self._execute_steps()
            self._complete_task()
        except Exception as e:
            self._handle_failure(e)
            raise

    def _execute_steps(self):
        """执行所有步骤"""
        try:
            # 先刷新任务对象
            self.db.refresh(self.task)
            # 更新总步骤数
            self.task.total_steps = len(self.steps)
            # 更新任务状态
            self.task.status = TaskStatus.PROCESSING.value
            self.task.progress = TaskProgress.PROCESSING.value
            self.task.progress_message = "开始执行任务"
            self.db.commit()
            
            # 验证更新是否成功
            self.db.refresh(self.task)
            if self.task.total_steps != len(self.steps):
                raise Exception("更新任务总步骤数失败")
                
            # 执行步骤
            for i, step in enumerate(self.steps[self.start_step:], self.start_step):
                self._execute_single_step(step, i)
                
        except Exception as e:
            self.db.rollback()
            raise Exception(f"执行步骤失败: {str(e)}")

    def _execute_single_step(self, step: BaseStep, step_index: int):
        """执行单个步骤"""
        self.context_manager.set('current_step_index', step_index)
        self._update_step_progress(step, step_index, 0, "开始执行")
        
        try:
            if self._should_execute_step(step):
                result = step.execute()
                self._handle_step_success(step, result, step_index)
            else:
                self._load_completed_step(step, step_index)
        except Exception as e:
            self._handle_step_failure(step, e)
            raise

    def _should_execute_step(self, step: BaseStep) -> bool:
        """检查步骤是否需要执行"""
        if self.is_retry and step.name == self.task.current_step:
            return True
        return not all(
            os.path.exists(os.path.join(self.temp_dir, output))
            for output in step.output_files
        )

    def _handle_step_success(self, step: BaseStep, result: Dict, step_index: int):
        """处理步骤执行成功"""
        self.context_manager.update(result)
        self._update_step_progress(step, step_index, 100, "执行完成")

    def _handle_step_failure(self, step: BaseStep, error: Exception):
        """处理步骤执行失败"""
        error_msg = str(error)
        log.error(f"步骤 {step.name} 执行失败: {error_msg}")
        self.task.current_step = step.name
        self.progress_tracker.update_error(error_msg)
        self.db.commit()

    def _handle_failure(self, error: Exception):
        """处理任务失败"""
        error_msg = str(error)
        if not isinstance(error, TaskError):
            error_msg = f"任务执行异常: {error_msg}"
        
        self.progress_tracker.update_error(error_msg)
        self.context_manager.set('status', TaskStatus.FAILED.value)
        self.context_manager.save()

    def _update_step_progress(self, step: BaseStep, step_index: int, 
                            progress: int, message: str):
        """更新步骤进度"""
        self.progress_tracker.update_progress(
            step_index=step_index,
            step_name=step.name,
            progress=progress,
            message=f"{message}"
        )

    def _complete_task(self):
        """完成任务"""
        self.db.refresh(self.task)
        self.task.status = TaskStatus.COMPLETED.value
        self.task.progress = TaskProgress.COMPLETED.value
        self.context_manager.save()
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise Exception(f"更新任务状态失败: {str(e)}")


    def _get_start_step(self, is_retry: bool) -> int:
        """获取起始步骤"""
        if not is_retry or not self.task.current_step:
            return 0
        try:
            return [step.name for step in self.steps].index(self.task.current_step)
        except ValueError:
            return 0
        
    def _load_completed_step(self, step: BaseStep, step_index: int):
        """加载已完成的步骤"""
        step_outputs = self._load_step_outputs(step)
        self.context_manager.update(step_outputs)
        
        self.progress_tracker.update_progress(
            step_index=step_index,
            step_name=step.name,
            progress=100,
            message=f"{step.name} 已完成"
        )