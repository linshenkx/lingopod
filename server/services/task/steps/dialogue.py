import json
import os
from typing import Dict, List

from services.task.utils.context import ContextManager
from .base import BaseStep
from services.llm import LLMService
from core.logging import log
from services.task.utils.progress_tracker import ProgressTracker
from utils.prompt_utils import PromptUtils
from langchain_core.output_parsers import JsonOutputParser

class DialogueStep(BaseStep):
    def __init__(
        self,
        level: str,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name=f"生成{level}对话内容",
            input_files=[f"{level}/content.txt"],
            output_files=[f"{level}/dialogue_en.json"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.level = level
        self.llm_service = LLMService()
        context_manager.set("current_level", level)  # 添加这行，确保当前level被设置
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行对话生成步骤"""
        try:
            level_dir = context_manager.get("level_dir")
            log.info(f"获取到level_dir: {level_dir}")
            
            if not level_dir:
                raise ValueError(f"缺少{self.level}难度等级目录")
            
            content_filename = context_manager.get(f"{self.level}/content.txt")
            log.info(f"获取到content_filename: {content_filename}")
            
            if not content_filename:
                raise ValueError("缺少页面内容")
            
            # 从文件读取内容    
            content_path = os.path.join(level_dir, content_filename)
            
            text_content = open(content_path, 'r', encoding='utf-8').read()
            
            if not text_content:
                raise ValueError("页面内容为空")
            
            # 获取风格参数
            style_params = context_manager.get("style_params", {})
            
            log.info(f"开始生成{self.level}难度对话内容")
            dialogue = self.generate_dialogue(
                text_content,
                level=self.level,
                style_params=style_params
            )
            
            # 添加输出验证
            if not dialogue:
                raise ValueError("生成的对话内容为空")
            
            # 验证对话格式
            if not isinstance(dialogue, list):
                raise ValueError(f"对话格式错误：期望列表格式，实际得到 {type(dialogue)}")
            
            # 验证对话长度
            if len(dialogue) < 2:  # 至少需要两轮对话
                raise ValueError(f"对话长度不足：只有 {len(dialogue)} 轮对话")
            
            # 保存对话内容到文件
            dialogue_path = os.path.join(level_dir, "dialogue_en.json")
            log.info(f"构造对话文件路径: {dialogue_path}")
            
            with open(dialogue_path, 'w', encoding='utf-8') as f:
                json.dump(dialogue, f, ensure_ascii=False, indent=2)
            
            # 修改结果构造部分
            result = {
                f"{self.level}/dialogue_en.json": "dialogue_en.json"
            }
            
            log.info(f"返回结果: {result}")
            
            # 验证返回值完整性
            if not all(result.values()):
                log.error(f"返回结果验证失败: {result}")
                raise ValueError("返回结果不完整")
            
            # 验证输出文件是否存在
            output_path = os.path.join(level_dir, dialogue_path)
            if not os.path.exists(output_path):
                log.error(f"输出文件不存在: {output_path}")
                raise ValueError(f"输出文件不存在: {output_path}")
            
            return result
            
        except Exception as e:
            log.error(f"对话生成步骤执行失败: {str(e)}")
            raise
        
    def generate_dialogue(self, text_content: str, level: str, style_params: Dict = None) -> List[Dict]:
        """生成对话内容
        
        Args:
            text_content: 原始文本内容
            level: 难度等级 (elementary/intermediate/advanced)
            style_params: 风格参数，可包含：
                - length: 对话长度 (short/medium/long)
                - tone: 语气风格 (formal/casual/humorous)
                - emotion: 情感色彩 (neutral/positive/negative)
                - professionalism: 专业程度 (basic/moderate/expert)
        """
        try:
            # 根据难度等级选择不同的提示模板
            template_name = f"dialogue_generation_{level}"
            chat_prompt = PromptUtils.create_chat_prompt(template_name)
            chain = chat_prompt | self.llm_service.llm | JsonOutputParser()
            
            # 添加进度更新
            current_step_index = self.context_manager.get('current_step_index', 0)
            self.progress_tracker.update_progress(
                step_index=current_step_index,
                step_name=self.name,
                progress=30,
                message="正在生成对话内容..."
            )
            
            # 准备输入参数
            inputs = {
                "text_content": text_content[:2000],  # 限制输入长度
                "level": level,
                "style_params": style_params or {}
            }
            
            # 多次重试
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    result = chain.invoke(inputs)
                    
                    # 添加更详细的验证
                    if not result:
                        raise ValueError("对话生成结果为空")
                        
                    if not isinstance(result, list):
                        raise ValueError(f"对话生成结果格式错误：期望列表格式，实际得到 {type(result)}")
                        
                    # 验证每个对话项
                    for i, item in enumerate(result):
                        if not isinstance(item, dict):
                            raise ValueError(f"对话项 {i} 格式错误：期望字典格式，实际得到 {type(item)}")
                            
                        if "role" not in item:
                            raise ValueError(f"对话项 {i} 缺少 'role' 字段")
                            
                        if "content" not in item:
                            raise ValueError(f"对话项 {i} 缺少 'content' 字段")
                            
                        if not item["role"] in ["host", "guest"]:
                            raise ValueError(f"对话项 {i} 的 'role' 值无效：{item['role']}")
                            
                        if not isinstance(item["content"], str) or not item["content"].strip():
                            raise ValueError(f"对话项 {i} 的 'content' 为空或格式错误")
                            
                    # 更新进度
                    self.progress_tracker.update_progress(
                        step_index=current_step_index,
                        step_name=self.name,
                        progress=90,
                        message="对话生成完成"
                    )
                    
                    return result
                    
                except Exception as e:
                    last_error = e
                    log.warning(f"对话生成第{attempt + 1}次尝试失败: {str(e)}")
                    if attempt < max_retries - 1:
                        # 更新进度
                        self.progress_tracker.update_progress(
                            step_index=current_step_index,
                            step_name=self.name,
                            progress=30 + attempt * 20,
                            message=f"对话生成重试中({attempt + 1}/{max_retries})..."
                        )
                    continue
                    
            # 所有重试都失败了
            error_msg = f"对话生成失败({max_retries}次尝试): {str(last_error)}"
            log.error(error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            log.error(f"对话生成发生错误: {str(e)}")
            raise Exception(f"对话生成失败: {str(e)}")