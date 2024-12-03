from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from core.config import settings
from core.logging import log
from typing import List, Dict
from utils.prompt_utils import PromptUtils

class LLMService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=settings.MODEL,
            openai_api_key=settings.API_KEY,
            openai_api_base=settings.API_BASE_URL
        )
        
    def generate_dialogue(self, text_content: str) -> List[Dict]:
        """生成对话内容"""
        try:
            chat_prompt = PromptUtils.create_chat_prompt("dialogue_generation")
            chain = chat_prompt | self.llm | JsonOutputParser()
            return chain.invoke({"text_content": text_content})
        except Exception as e:
            log.error(f"对话生成失败: {str(e)}")
            return []
