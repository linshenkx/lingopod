import json
import os
from typing import Dict, List

from services.task.utils.context import ContextManager
from .base import BaseStep
from services.llm import LLMService
from core.logging import log
from services.task.utils.progress_tracker import ProgressTracker

class DialogueStep(BaseStep):
    def __init__(
        self,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name="生成对话内容",
            input_files=["content.json"],
            output_files=["dialogue_cn.json"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.llm_service = LLMService()
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行对话生成步骤"""
        content_filename = context_manager.get("content.json")
        if not content_filename:
            raise ValueError("缺少页面内容")
        
        # 从文件读取内容    
        temp_dir = context_manager.get("temp_dir")
        content_path = os.path.join(temp_dir, content_filename)
        
        with open(content_path, 'r', encoding='utf-8') as f:
            content_data = json.load(f)
            text_content = content_data.get("content")
        
        if not text_content:
            raise ValueError("页面内容为空")
            
        log.info("开始生成对话内容")
        dialogue = self.llm_service.generate_dialogue(text_content)
        if not dialogue:
            raise ValueError("对话生成失败")
            
        # 保存对话内容到文件
        task_id = context_manager.get("taskId")
        dialogue_filename = f"{task_id}_cn.json"
        dialogue_path = os.path.join(temp_dir, dialogue_filename)
        
        with open(dialogue_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue, f, ensure_ascii=False, indent=2)
        
        return {
            "dialogue_cn.json": dialogue_filename
        }
