from pydantic import BaseModel, Field, ValidationError, field_validator, ConfigDict
from typing import Optional, List, Dict, Literal
from utils.time_utils import TimeUtil
from datetime import datetime
import re
from core.config import settings

# 基础任务属性
class TaskBase(BaseModel):
    url: str = Field(..., description="任务URL")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        # 获取允许的URL模式
        pattern = settings.ALLOWED_URL_PATTERN
        if not re.match(pattern, str(v)):
            raise ValueError(f'URL必须匹配模式: {pattern}')
        return v

# 对话风格参数
class StyleParams(BaseModel):
    """对话风格参数"""
    content_length: Literal["short", "medium", "long"] = Field(
        default="medium",
        description="对话长度: short(5-8轮), medium(8-12轮), long(12-15轮)"
    )
    tone: Literal["casual", "formal", "humorous"] = Field(
        default="casual",
        description="对话语气: casual(轻松), formal(正式), humorous(幽默)"
    )
    emotion: Literal["neutral", "enthusiastic", "professional"] = Field(
        default="neutral",
        description="情感色彩: neutral(中性), enthusiastic(热情), professional(专业)"
    )

# 媒体文件
class MediaFiles(BaseModel):
    """媒体文件"""
    audio: Optional[str] = Field(None, description="音频文件URL")
    subtitle: Optional[str] = Field(None, description="字幕文件URL")

# 语言文件
class LanguageFiles(BaseModel):
    """语言文件"""
    en: Optional[MediaFiles] = Field(None, description="英文文件")
    cn: Optional[MediaFiles] = Field(None, description="中文文件")

# 创建任务时的请求模型
class TaskCreate(TaskBase):
    is_public: bool = Field(default=False, description="是否公开")
    style_params: Optional[StyleParams] = Field(
        default_factory=StyleParams,
        description="对话风格参数"
    )

# 更新任务时的请求模型
class TaskUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[str] = None
    title: Optional[str] = None
    current_step: Optional[str] = None
    total_steps: Optional[int] = Field(None, ge=0)
    step_progress: Optional[int] = Field(None, ge=0, le=100)
    is_public: Optional[bool] = None
    style_params: Optional[StyleParams] = None

    @field_validator('step_progress')
    @classmethod
    def validate_step_progress(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError('Step progress must be between 0 and 100')
        return v

# 完整任务响应模型
class TaskResponse(TaskBase):
    """完整任务响应模型"""
    model_config = ConfigDict(from_attributes=True)

    taskId: str
    status: str
    progress: str
    title: Optional[str] = None
    created_at: int
    updated_at: int
    is_public: bool
    style_params: StyleParams
    files: Dict[str, LanguageFiles] = Field(
        default_factory=dict,
        description="按难度等级和语言组织的文件, 如: {'elementary': {'en': {...}, 'cn': {...}}}"
    )
    error: Optional[str] = None
    current_step: Optional[str] = None
    current_step_index: Optional[int] = None
    total_steps: Optional[int] = None
    step_progress: Optional[int] = None
    progress_message: Optional[str] = None

# 任务查询参数模型
class TaskQueryParams(BaseModel):
    status: Optional[str] = Field(None, description="任务状态")
    start_date: Optional[int] = Field(None, description="开始时间(毫秒时间戳)")
    end_date: Optional[int] = Field(None, description="结束时间(毫秒时间戳)")
    is_public: Optional[bool] = Field(None, description="是否公开")
    user_id: Optional[int] = Field(None, description="用户ID")
    title_keyword: Optional[str] = Field(None, description="标题关键词")
    url_keyword: Optional[str] = Field(None, description="URL关键词")
    limit: int = Field(10, ge=1, le=100, description="每页数量")
    offset: int = Field(0, ge=0, description="偏移量")

# 任务列表响应模型
class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]
