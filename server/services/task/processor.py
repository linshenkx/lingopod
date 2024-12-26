from typing import List, Dict
import sqlalchemy
from sqlalchemy.orm import Session
import os
import time
import json

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
from services.task.steps.fetch_content import FetchContentStep
from services.task.steps.generate_title import GenerateTitleStep

class TaskProcessor:
    """任务处理器"""
    
    def __init__(self, task: Task, db: Session, is_retry: bool = False):
        self.task = task
        self.db = db
        self.is_retry = is_retry
        self.temp_dir = os.path.join(settings.TASK_DIR, task.taskId)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.context_manager = ContextManager(task, self.temp_dir)
        
        # 创建难度等级目录
        self.level_dirs = {}
        for level in ["elementary", "intermediate", "advanced"]:
            level_dir = os.path.join(self.temp_dir, level)
            os.makedirs(level_dir, exist_ok=True)
            self.level_dirs[level] = level_dir
            # 将level_dir添加到上下文，使用level作为前缀
            self.context_manager.set(f"{level}_dir", level_dir)
        
        self.steps = self._create_steps_without_tracker()
        self.progress_tracker = ProgressTracker(task, db, len(self.steps))
        self._update_steps_tracker()
        self.start_step = self._get_start_step(is_retry)
        
    def _create_steps_without_tracker(self) -> List[BaseStep]:
        """创建处理步骤列表(不包含progress_tracker)"""
        base_params = {
            "progress_tracker": None,
            "context_manager": self.context_manager
        }
        
        steps = [
            # 添加通用步骤
            FetchContentStep(**base_params),  # 确保这是第一个步骤
            GenerateTitleStep(**base_params),
        ]
        
        # 为每个难度等级创建步骤
        for level in ["elementary", "intermediate", "advanced"]:
            level_steps = [
                ContentStep(level=level, **base_params),
                DialogueStep(level=level, **base_params),
                TranslationStep(level=level, **base_params)
            ]
            
            # 需要中英文处理的步骤类
            bilingual_steps = [
                (AudioStep, "音频生成"),
                (SubtitleStep, "字幕生成"), 
                (AudioMergeStep, "音频合并")
            ]
            
            # 添加中英文步骤
            for step_class, _ in bilingual_steps:
                for lang in ["cn", "en"]:
                    level_steps.append(
                        step_class(level=level, lang=lang, **base_params)
                    )
            
            steps.extend(level_steps)
                
        return steps

    def _update_steps_tracker(self):
        """更新所有步骤的progress_tracker"""
        for step in self.steps:
            step.progress_tracker = self.progress_tracker

    def process_task(self, timeout: int = None):
        """处理任务
        
        Args:
            timeout (int, optional): 任务执行超时时间(秒)。默认为None，表示不设置超时。
        """
        task_id = self.task.taskId  # 预先保存taskId
        log.info(f"开始处理任务: {task_id}")
        try:
            start_time = time.time()
            self._execute_steps(timeout=timeout)
            self._complete_task()
            log.info(f"任务处理完成: {task_id}")
        except Exception as e:
            log.error(f"任务处理失败: {task_id}, error: {str(e)}")
            try:
                self._handle_failure(e)
            except (sqlalchemy.orm.exc.ObjectDeletedError, sqlalchemy.exc.InvalidRequestError):
                # 任务已被删除，记录日志并优雅退出
                log.warning(f"Task has been deleted during processing: {task_id}")
                return
            raise

    def _execute_steps(self, timeout: int = None):
        """执行所有步骤
        
        Args:
            timeout (int, optional): 任务执行超时时间(秒)
        """
        try:
            # 先刷新任务对象
            log.info(f"刷新任务对象: {self.task.taskId}")
            self.db.refresh(self.task)
            
            # 更新总步骤数
            self.task.total_steps = len(self.steps)
            # 更新任务状态
            self.task.status = TaskStatus.PROCESSING.value
            self.task.progress = TaskProgress.PROCESSING.value
            self.task.progress_message = "开始执行任务"
            
            log.info(f"更新任务初始状态: taskId={self.task.taskId}, total_steps={len(self.steps)}")
            self.db.commit()
            
            # 验证更新是否成功
            self.db.refresh(self.task)
            if self.task.total_steps != len(self.steps):
                raise Exception(f"更新任务总步骤数失败: expected={len(self.steps)}, actual={self.task.total_steps}")
            
            start_time = time.time()
            # 执行步骤
            for i, step in enumerate(self.steps[self.start_step:], self.start_step):
                if timeout and (time.time() - start_time) > timeout:
                    raise Exception(f"任务执行超时(超过{timeout}秒)")
                    
                log.info(f"开始执行步骤: taskId={self.task.taskId}, step={step.name}, index={i}")
                self._execute_single_step(step, i)
                log.info(f"步骤执行完成: taskId={self.task.taskId}, step={step.name}, index={i}")
                
        except sqlalchemy.exc.InvalidRequestError as e:
            # 任务可能已被删除，记录日志
            log.error(f"Task refresh failed, task may have been deleted: {str(e)}")
            self.db.rollback()
            raise Exception(f"任务可能已被删除: {str(e)}")
        except Exception as e:
            log.error(f"执行步骤失败: {str(e)}")
            self.db.rollback()
            raise Exception(f"执行步骤失败: {str(e)}")

    def _execute_single_step(self, step: BaseStep, step_index: int):
        """执行单个步骤"""
        level = getattr(step, 'level', None)
        if level:
            self.context_manager.set('current_level', level)
            self.context_manager.set('level_dir', self.level_dirs[level])
            
        self.context_manager.set('current_step_index', step_index)
        self._update_step_progress(step, step_index, 0, "开始执行")
        
        try:
            if self._should_execute_step(step):
                log.info(f"步骤 {step.name} 需要执行")
                result = step.execute()
                self._handle_step_success(step, result, step_index)
            else:
                log.info(f"步骤 {step.name} 已完成，跳过执行")
                self._load_completed_step(step, step_index)
        except Exception as e:
            self._handle_step_failure(step, e)
            raise

    def _should_execute_step(self, step: BaseStep) -> bool:
        """检查步骤是否需要执行"""
        if self.is_retry and step.name == self.task.current_step:
            return True
        
        for output in step.output_files:
            # 检查文件是否在temp_dir中存在
            file_exists = os.path.exists(os.path.join(self.temp_dir, output))
            # 检查context manager中是否有输出且值不为空
            context_value = self.context_manager.get(output)
            context_exists = context_value is not None and context_value != ""
            
            # 如果文件既不在temp_dir也不在context_manager中，需要执行步骤
            if not (file_exists or context_exists):
                return True
        
        return False

    def _handle_step_success(self, step: BaseStep, result: Dict, step_index: int):
        """处理步骤执行成功"""
        # level = getattr(step, 'level', None)
        # if level and result:
        #     # 更新文件URL到task.files
        #     if not self.task.files:
        #         self.task.files = {}
        #     if level not in self.task.files:
        #         self.task.files[level] = {}
                
        #     lang = getattr(step, 'lang', None)
        #     if lang and 'audio' in result:
        #         if lang not in self.task.files[level]:
        #             self.task.files[level][lang] = {}
        #         self.task.files[level][lang].update(result)
        
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
        task_id = self.task.taskId  # 预先保存taskId
        try:
            error_msg = str(error)
            if not isinstance(error, TaskError):
                error_msg = f"任务执行异常: {error_msg}"
            
            self.progress_tracker.update_error(error_msg)
            self.context_manager.set('status', TaskStatus.FAILED.value)
            self.context_manager.save()
        except (sqlalchemy.orm.exc.ObjectDeletedError, sqlalchemy.exc.InvalidRequestError) as e:
            # 任务已被删除，记录日志
            log.warning(f"Cannot update error status, task has been deleted: {task_id}")
            raise  # 重新抛出异常以便上层处理

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

    def _load_step_outputs(self, step: BaseStep) -> Dict:
        """加载已完成步骤的输出文件内容
        
        Args:
            step: BaseStep对象
            
        Returns:
            Dict: 包含步骤输出文件的字典
        """
        result = {}
        level = getattr(step, 'level', None)
        check_dir = self.level_dirs.get(level, self.temp_dir) if level else self.temp_dir
        
        for output_file in step.output_files:
            # 获取实际的文件名
            filename = os.path.basename(output_file)
            file_path = os.path.join(check_dir, filename)
            
            if os.path.exists(file_path):
                # 如果文件存在，将其添加到结果中
                result[output_file] = filename
                
                # 如果是JSON文件，读取内容并更新上下文
                if filename.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        if isinstance(content, dict):
                            result.update(content)
        
        return result