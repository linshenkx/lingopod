from typing import Dict
import os
import json

from services.task.utils.progress_tracker import ProgressTracker
from services.task.steps.base import BaseStep
from services.task.utils.context import ContextManager
from services.llm import LLMService
from utils.prompt_utils import PromptUtils
from core.logging import log


class ContentStep(BaseStep):
    def __init__(
        self,
        level: str,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name=f"处理{level}难度内容",
            input_files=["raw_content.txt", "title"],
            output_files=[f"{level}/content.txt"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.level = level
        self.llm_service = LLMService()
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行内容处理步骤"""
        level_dir = context_manager.get("level_dir")
        if not level_dir:
            raise ValueError(f"缺少{self.level}难度等级目录")
            
        raw_content = context_manager.get("raw_content")
        title = context_manager.get("title")
        
        if not raw_content:
            raise ValueError("缺少原始内容")
        if not title:
            raise ValueError("缺少标题")
            
        # 根据难度等级处理内容
        processed_content = self._process_content_by_level(raw_content)
        
        # 保存处理后的内容到文件
        content_path = os.path.join(level_dir, "content.txt")
        
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(processed_content)
            
        return {
            f"{self.level}/content.txt": "content.txt"
        }
        
    def _process_content_by_level(self, content: str) -> str:
        """根据难度等级处理内容"""
        log.info(f"开始处理{self.level}难度内容")
        try:
            template_name = f"content_processing_{self.level}"
            chat_prompt = PromptUtils.create_chat_prompt(template_name)
            chain = chat_prompt | self.llm_service.llm
            
            response = chain.invoke({
                "content": content,
                "level": self.level,
                "style_params": self.context_manager.get("style_params", {})
            })
            
            processed_content = response.content if hasattr(response, 'content') else str(response)
            if not processed_content or not processed_content.strip():
                raise ValueError("处理后的内容为空")
            
            processed_content = processed_content.strip()
            log.info(f"成功处理{self.level}难度内容")
            return processed_content
            
        except Exception as e:
            log.error(f"处理{self.level}难度内容失败: {str(e)}")
            raise ValueError(f"内容处理失败: {str(e)}")
