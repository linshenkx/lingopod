from typing import Dict
import os
import json

from services.task.utils.progress_tracker import ProgressTracker
from services.task.steps.base import BaseStep
from services.task.utils.context import ContextManager
from services.llm import LLMService
from utils.prompt_utils import PromptUtils
from core.logging import log

class GenerateTitleStep(BaseStep):
    def __init__(
        self,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name="生成标题",
            input_files=["raw_content"],
            output_files=["title"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.llm_service = LLMService()
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行标题生成步骤"""
        raw_title = context_manager.get("raw_title")
        raw_content = context_manager.get("raw_content")
        if not raw_content:
            raise ValueError("缺少原始内容")
            
        # 如果原始标题为空或无效,使用LLM生成标题
        title = raw_title if raw_title else self._generate_title(raw_content)
        if not title or title == "无标题":
            raise ValueError("无法获取或生成有效的标题")
            
        # # 获取context文件路径
        # temp_dir = self.context_manager.get("temp_dir")
        # context_path = os.path.join(temp_dir, "context.json")
        
        # # 读取现有context
        # with open(context_path, 'r', encoding='utf-8') as f:
        #     context_data = json.load(f)
        
        # # 更新title
        # context_data['title'] = title
        
        # # 保存更新后的context
        # with open(context_path, 'w', encoding='utf-8') as f:
        #     json.dump(context_data, f, ensure_ascii=False, indent=2)
        
        # 更新任务标题
        self.progress_tracker.db.refresh(self.progress_tracker.task)
        self.progress_tracker.task.title = title
        try:
            self.progress_tracker.db.commit()
        except Exception as e:
            self.progress_tracker.db.rollback()
            raise Exception(f"更新任务标题失败: {str(e)}")
            
        return {
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