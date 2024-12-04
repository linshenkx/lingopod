from pydantic import BaseModel, AnyHttpUrl, Field, field_validator
from typing import Optional, List, Dict
from utils.time_utils import TimeUtil
from datetime import datetime
import re
from core.config import settings

# 基础任务属性
class TaskBase(BaseModel):
    url: AnyHttpUrl = Field(..., description="任务URL")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        # 获取允许的URL模式
        pattern = settings.ALLOWED_URL_PATTERN
        if not re.match(pattern, str(v)):
            raise ValueError(f'URL必须匹配模式: {pattern}')
        return v

# 创建任务时的请求模型
class TaskCreate(TaskBase):
    is_public: bool = Field(default=False, description="是否公开")

# 更新任务时的请求模型
class TaskUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[str] = None
    title: Optional[str] = None
    dialogue: Optional[List[Dict]] = None
    current_step: Optional[str] = None
    total_steps: Optional[int] = Field(None, ge=0)
    step_progress: Optional[int] = Field(None, ge=0, le=100)
    audioUrlCn: Optional[str] = None
    audioUrlEn: Optional[str] = None
    subtitleUrlCn: Optional[str] = None
    subtitleUrlEn: Optional[str] = None
    is_public: Optional[bool] = None

    @field_validator('step_progress')
    @classmethod
    def validate_step_progress(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError('Step progress must be between 0 and 100')
        return v

# 完整任务响应模型
class TaskResponse(BaseModel):
    taskId: str
    url: str
    status: str
    progress: str
    title: Optional[str] = None
    current_step: Optional[str] = None
    current_step_index: Optional[int] = None
    total_steps: Optional[int] = None
    step_progress: Optional[int] = None
    audioUrlCn: Optional[str] = None
    audioUrlEn: Optional[str] = None
    subtitleUrlCn: Optional[str] = None
    subtitleUrlEn: Optional[str] = None
    is_public: bool = False
    user_id: int
    created_by: int
    updated_by: Optional[int] = None
    createdAt: int = Field(..., description="创建时间（毫秒时间戳）")
    updatedAt: int = Field(..., description="更新时间（毫秒时间戳）")
    progress_message: Optional[str] = None

    class Config:
        from_attributes = True

class TaskQueryParams(BaseModel):
    """任务查询参数模型"""
    status: Optional[str] = Field(None, description="任务状态")
    start_date: Optional[int] = Field(None, description="开始时间(毫秒时间戳)")
    end_date: Optional[int] = Field(None, description="结束时间(毫秒时间戳)")
    is_public: Optional[bool] = Field(None, description="是否公开")
    user_id: Optional[int] = Field(None, description="用户ID")
    title_keyword: Optional[str] = Field(None, description="标题关键词")
    url_keyword: Optional[str] = Field(None, description="URL关键词")
    limit: int = Field(10, ge=1, le=100, description="每页数量")
    offset: int = Field(0, ge=0, description="偏移量")

# 删除 TaskList 类，修改 TaskListResponse
class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]
