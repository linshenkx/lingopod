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
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name="翻译对话内容",
            input_files=["dialogue_cn.json"],
            output_files=["dialogue_en.json"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.llm_service = LLMService()
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行翻译步骤"""
        dialogue_filename = context_manager.get("dialogue_cn.json")
        if not dialogue_filename:
            raise ValueError("缺少中文对话内容")
        
        # 从文件读取对话内容    
        temp_dir = context_manager.get("temp_dir")
        dialogue_path = os.path.join(temp_dir, dialogue_filename)
        
        with open(dialogue_path, 'r', encoding='utf-8') as f:
            dialogue = json.load(f)
        
        if not dialogue:
            raise ValueError("对话内容为空")
            
        translated_dialogue = self._translate_dialogue(dialogue)
        
        # 保存翻译结果到文件
        task_id = context_manager.get("taskId")
        dialogue_filename = f"{task_id}_en.json"
        dialogue_path = os.path.join(temp_dir, dialogue_filename)
        
        # 将翻译内容写入文件
        with open(dialogue_path, 'w', encoding='utf-8') as f:
            json.dump(translated_dialogue, f, ensure_ascii=False, indent=2)
        
        return {
            "dialogue_en.json": dialogue_filename
        }
        
    def _translate_dialogue(self, dialogue: List[Dict]) -> List[Dict]:
        """批量翻译对话内容"""
        log.info("开始翻译对话内容")
        
        chat_prompt = PromptUtils.create_chat_prompt("dialogue_translation")
        chain = chat_prompt | self.llm_service.llm | JsonOutputParser()
        
        translated_dialogue = []
        batch_size = 5
        
        for i in range(0, len(dialogue), batch_size):
            batch = dialogue[i:i+batch_size]
            log.info(f"正在翻译第 {i+1} 到 {min(i+batch_size, len(dialogue))} 条对话")
            
            try:
                batch_translated = chain.invoke({"content": batch})
                translated_dialogue.extend(batch_translated)
                log.info(f"成功翻译批次,共 {len(batch_translated)} 条对话")
            except Exception as e:
                log.error(f"翻译批次失败: {str(e)}, 尝试逐条翻译")
                # 批次翻译失败时逐条翻译
                for item in batch:
                    try:
                        single_translated = chain.invoke({"content": [item]})
                        translated_dialogue.extend(single_translated)
                    except Exception as e:
                        log.error(f"单条翻译失败: {str(e)}")
                        translated_dialogue.append({
                            "role": item["role"],
                            "content": ""
                        })
                        
        return translated_dialogue
