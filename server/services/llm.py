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


