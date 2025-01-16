from typing import Optional
from pydantic import BaseModel, HttpUrl, Field, model_validator
from core.config import settings

class RSSFeedBase(BaseModel):
    """RSS源基础模型"""
    url: HttpUrl
    title: Optional[str] = Field(
        default=None,
        description="RSS源标题，如果不指定则自动从源获取"
    )
    fetch_interval: Optional[int] = Field(
        default=settings.RSS_DEFAULT_FETCH_INTERVAL_SECONDS,
        description="抓取间隔（秒）",
        ge=settings.RSS_MIN_FETCH_INTERVAL,
        le=settings.RSS_MAX_FETCH_INTERVAL
    )
    initial_entries_count: Optional[int] = Field(
        default=2,
        description="首次获取的条目数量",
        ge=1
    )
    update_entries_count: Optional[int] = Field(
        default=1,
        description="后续更新的条目数量",
        ge=1
    )

    @model_validator(mode='before')
    @classmethod
    def validate_url(cls, data):
        if isinstance(data, dict) and 'url' in data:
            if isinstance(data['url'], str):
                data['url'] = HttpUrl(data['url'])
        return data

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        if 'url' in data:
            data['url'] = str(data['url'])
        return data

class RSSFeedCreate(RSSFeedBase):
    """创建RSS源的请求模型"""
    pass

class RSSFeedUpdate(BaseModel):
    """更新RSS源的请求模型"""
    title: Optional[str] = Field(
        default=None,
        description="RSS源标题"
    )
    fetch_interval: Optional[int] = Field(
        default=None,
        description="抓取间隔（秒）",
        ge=settings.RSS_MIN_FETCH_INTERVAL,
        le=settings.RSS_MAX_FETCH_INTERVAL
    )
    initial_entries_count: Optional[int] = Field(
        default=None,
        description="首次获取的条目数量",
        ge=1
    )
    update_entries_count: Optional[int] = Field(
        default=None,
        description="后续更新的条目数量",
        ge=1
    )

class RSSFeedList(RSSFeedBase):
    """RSS源列表响应模型"""
    id: int
    title: Optional[str] = None
    user_id: int
    last_fetch: Optional[int] = None
    is_active: bool
    error_count: int
    created_at: int
    updated_at: int

    class Config:
        from_attributes = True

class RSSFeedResponse(RSSFeedList):
    """RSS源详情响应模型"""
    pass

class RSSEntryBase(BaseModel):
    """RSS条目基础模型"""
    guid: str
    title: Optional[str] = None
    link: Optional[str] = None
    published: Optional[int] = None

class RSSEntryResponse(RSSEntryBase):
    """RSS条目响应模型"""
    id: int
    feed_id: int
    processed: bool
    task_id: Optional[str] = None
    created_at: int
    updated_at: int

    class Config:
        from_attributes = True
