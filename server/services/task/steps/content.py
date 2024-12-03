from typing import Dict, Optional
import os
import json

from services.task.utils.progress_tracker import ProgressTracker
from .base import BaseStep
from services.url_fetcher import fetch_url_content
from services.task.utils.context import ContextManager
from services.llm import LLMService
from utils.prompt_utils import PromptUtils
from core.logging import log


class ContentStep(BaseStep):
    def __init__(
        self,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name="获取页面内容",
            input_files=[],
            output_files=["content.json"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.llm_service = LLMService()
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行内容获取步骤"""
        url = context_manager.get("url")
        if not url:
            raise ValueError("缺少URL")
            
        text_content, title = fetch_url_content(url)
        if not text_content or len(text_content) < 4:
            raise ValueError("获取页面内容失败或内容太短")
            
        # 如果标题为空，使用LLM生成标题
        if not title:
            title = self._generate_title(text_content)
            if not title or title == "无标题":
                raise ValueError("无法获取或生成有效的标题")
            
        # 保存内容到文件
        task_id = context_manager.get("taskId")
        temp_dir = context_manager.get("temp_dir")
        content_filename = f"{task_id}_content.json"
        content_path = os.path.join(temp_dir, content_filename)
        
        with open(content_path, 'w', encoding='utf-8') as f:
            json.dump({
                "content": text_content,
                "title": title
            }, f, ensure_ascii=False, indent=2)
        
        # 更新任务标题
        self.progress_tracker.db.refresh(self.progress_tracker.task)
        self.progress_tracker.task.title = title
        try:
            self.progress_tracker.db.commit()
        except Exception as e:
            self.progress_tracker.db.rollback()
            raise Exception(f"更新任务标题失败: {str(e)}")
            
        return {
            "content.json": content_filename,
            "title": title
        }
        
    def _generate_title(self, content: str) -> str:
        """使用LLM生成标题"""
        log.info("开始生成播客标题")
        try:
            chat_prompt = PromptUtils.create_chat_prompt("podcast_title_generation")
            chain = chat_prompt | self.llm_service.llm
            response = chain.invoke({"content": content})
            title = response.content if hasattr(response, 'content') else str(response)
            if not title or not title.strip():
                raise ValueError("生成的标题为空")
            
            title = title.strip()
            log.info(f"成功生成播客标题: {title}")
            return title
        except Exception as e:
            log.error(f"生成标题失败: {str(e)}")
            raise ValueError(f"标题生成失败: {str(e)}")
