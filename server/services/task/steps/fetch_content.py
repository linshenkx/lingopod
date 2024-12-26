from typing import Dict
import os
import json

from services.task.utils.progress_tracker import ProgressTracker
from services.task.steps.base import BaseStep
from services.url_fetcher import fetch_url_content
from services.task.utils.context import ContextManager
from core.logging import log

class FetchContentStep(BaseStep):
    def __init__(
        self,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name="获取页面内容",
            input_files=[],
            output_files=["raw_content.txt","raw_title","raw_content"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行内容获取步骤"""
        url = context_manager.get("url")
        if not url:
            raise ValueError("缺少URL")
            
        text_content, raw_title = fetch_url_content(url)
        if not text_content or len(text_content) < 4:
            raise ValueError("获取页面内容失败或内容太短")
            
        # 保存原始内容到文件
        task_id = context_manager.get("taskId")
        content_filename = "raw_content.txt"
        content_path = os.path.join(self.context_manager.get("temp_dir"), content_filename)
        
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
            
        return {
            "raw_content.txt": content_filename,
            "raw_content": text_content,
            "raw_title": raw_title,
        }