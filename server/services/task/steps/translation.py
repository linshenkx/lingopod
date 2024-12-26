from typing import Dict, List
from .base import BaseStep
from services.llm import LLMService
from utils.prompt_utils import PromptUtils
from langchain_core.output_parsers import JsonOutputParser
from core.logging import log
from services.task.utils.context import ContextManager
from services.task.utils.progress_tracker import ProgressTracker
import os
import json

class TranslationStep(BaseStep):
    def __init__(
        self,
        level: str,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name=f"翻译{level}对话内容",
            input_files=[f"{level}/dialogue_en.json"],
            output_files=[f"{level}/dialogue_cn.json"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.level = level
        self.llm_service = LLMService()
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行翻译步骤"""
        level_dir = context_manager.get("level_dir")
        if not level_dir:
            raise ValueError(f"缺少{self.level}难度等级目录")
            
        dialogue_en_filename = context_manager.get(f"{self.level}/dialogue_en.json")
        if not dialogue_en_filename:
            raise ValueError("缺少英文对话内容")
        
        # 从文件读取对话内容    
        dialogue_path = os.path.join(level_dir, dialogue_en_filename)
        
        with open(dialogue_path, 'r', encoding='utf-8') as f:
            dialogue = json.load(f)
        
        if not dialogue:
            raise ValueError("对话内容为空")
            
        translated_dialogue = self._translate_dialogue(dialogue)
        
        # 保存翻译结果到文件
        dialogue_path = os.path.join(level_dir, "dialogue_cn.json")
        
        # 将翻译内容写入文件
        with open(dialogue_path, 'w', encoding='utf-8') as f:
            json.dump(translated_dialogue, f, ensure_ascii=False, indent=2)
        
        return {
            f"{self.level}/dialogue_cn.json": "dialogue_cn.json"
        }
        
    def _translate_dialogue(self, dialogue: List[Dict]) -> List[Dict]:
        """批量翻译对话内容"""
        log.info(f"开始翻译{self.level}难度对话内容")
        
        # 根据难度等级选择不同的翻译提示模板
        template_name = f"dialogue_translation_{self.level}"
        chat_prompt = PromptUtils.create_chat_prompt(template_name)
        chain = chat_prompt | self.llm_service.llm | JsonOutputParser()
        
        translated_dialogue = []
        batch_size = 5
        total = len(dialogue)
        
        for i in range(0, total, batch_size):
            batch = dialogue[i:i+batch_size]
            progress = int((i / total) * 100)
            self.progress_tracker.update_progress(
                step_index=int(self.context_manager.get('current_step_index', 0)),
                step_name=self.name,
                progress=progress,
                message=f"正在翻译第 {i+1} 到 {min(i+batch_size, total)} 条对话"
            )
            
            try:
                batch_translated = chain.invoke({
                    "content": batch,
                    "level": self.level,
                    "style_params": self.context_manager.get("style_params", {})
                })
                translated_dialogue.extend(batch_translated)
                log.info(f"成功翻译批次,共 {len(batch_translated)} 条对话")
            except Exception as e:
                log.error(f"翻译批次失败: {str(e)}, 尝试逐条翻译")
                # 批次翻译失败时逐条翻译
                for item in batch:
                    try:
                        single_translated = chain.invoke({
                            "content": [item],
                            "level": self.level,
                            "style_params": self.context_manager.get("style_params", {})
                        })
                        translated_dialogue.extend(single_translated)
                    except Exception as e:
                        log.error(f"单条翻译失败: {str(e)}")
                        translated_dialogue.append({
                            "role": item["role"],
                            "content": ""
                        })
                        
        return translated_dialogue
