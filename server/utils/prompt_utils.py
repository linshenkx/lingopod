import os
import yaml
from typing import Dict
from langchain_core.prompts import ChatPromptTemplate
from core.config import settings

class PromptUtils:
    @staticmethod
    def get_template_file() -> str:
        """获取模板文件路径"""
        return os.path.join(settings.BASE_DIR, 'server/core/prompts/prompt_templates.yaml')

    @classmethod
    def get_prompt_template(cls, template_name: str) -> Dict:
        """获取提示词模板"""
        template_file = cls.get_template_file()
        with open(template_file, 'r', encoding='utf-8') as f:
            templates = yaml.safe_load(f)
        
        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        return templates[template_name]

    @classmethod
    def create_chat_prompt(cls, template_name: str) -> ChatPromptTemplate:
        """创建聊天提示词模板"""
        template = cls.get_prompt_template(template_name)
        return ChatPromptTemplate.from_messages([
            ("system", template["system"]),
            ("human", template["human"]),
        ])
