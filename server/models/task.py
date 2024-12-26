from sqlalchemy import Column, String, BigInteger, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship, validates
from urllib.parse import urlparse
from db.base import Base
from models.enums import TaskProgress, TaskStatus
from utils.time_utils import TimeUtil


class Task(Base):
    """任务模型
    
    用于存储和管理任务的执行状态、进度和相关资源。支持多个英语等级的音频和字幕文件。
    """
    __tablename__ = "tasks"

    taskId = Column(String, primary_key=True)  # 任务唯一标识
    url = Column(String, nullable=False)  # 待处理的URL
    status = Column(String, nullable=False)  # 任务整体状态：pending/processing/completed/failed
    progress = Column(String, nullable=False)  # 当前步骤的执行状态：waiting/processing/completed/failed
    title = Column(String, nullable=True)  # 文章标题
    current_step = Column(String, nullable=True)  # 当前执行的步骤名称
    current_step_index = Column(Integer, nullable=True)  # 当前步骤序号
    total_steps = Column(Integer, nullable=True)  # 总步骤数
    step_progress = Column(Integer, nullable=True)  # 当前步骤的进度(0-100)
    
    # 风格参数
    style_params = Column(JSON, nullable=False, default={
        "content_length": "medium",
        "tone": "casual",
        "emotion": "neutral"
    })
    
    # 文件URL，按难度等级和语言组织
    # 格式: {
    #   "elementary": {
    #     "en": {"audio": "url", "subtitle": "url"},
    #     "cn": {"audio": "url", "subtitle": "url"}
    #   },
    #   "intermediate": {...},
    #   "advanced": {...}
    # }
    files = Column(JSON, nullable=False, default=dict)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 所属用户ID
    is_public = Column(Boolean, nullable=False, default=False)  # 是否公开
    created_by = Column(Integer, nullable=False)  # 创建者ID
    updated_by = Column(Integer, nullable=True)  # 更新者ID
    created_at = Column(BigInteger, nullable=False, default=TimeUtil.now_ms)  # 创建时间(毫秒时间戳)
    updated_at = Column(BigInteger, nullable=False, default=TimeUtil.now_ms, onupdate=TimeUtil.now_ms)  # 更新时间(毫秒时间戳)
    error = Column(String, nullable=True)  # 错误信息
    progress_message = Column(String, nullable=True)  # 进度消息
    
    # 关联关系
    user = relationship(
        "User",
        back_populates="tasks",
        foreign_keys=[user_id]
    )
    creator = relationship(
        "User",
        primaryjoin="Task.created_by == User.id",
        foreign_keys=[created_by],
        uselist=False
    )
    updater = relationship(
        "User",
        primaryjoin="Task.updated_by == User.id",
        foreign_keys=[updated_by],
        uselist=False
    )

    @validates('url')
    def validate_url(self, key, url):
        """验证URL格式"""
        if not url:
            raise ValueError("URL cannot be empty")
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        return url

    @validates('step_progress')
    def validate_step_progress(self, key, progress):
        """验证步骤进度值是否在有效范围内(0-100)"""
        if progress is not None and not (0 <= progress <= 100):
            raise ValueError("Step progress must be between 0 and 100, current progress: {}".format(progress))
        return progress

    @validates('status')
    def validate_status(self, key, status):
        """验证任务状态值是否有效"""
        if isinstance(status, str):
            status = TaskStatus(status)
        return status

    @validates('progress')
    def validate_progress(self, key, progress):
        """验证进度状态值是否有效"""
        if isinstance(progress, str):
            progress = TaskProgress(progress)
        return progress

    def to_response(self) -> dict:
        """转换为API响应格式"""
        return {
            "taskId": self.taskId,
            "url": self.url,
            "status": self.status,
            "progress": self.progress,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_public": self.is_public,
            "style_params": self.style_params,
            "files": self.files,
            "current_step": self.current_step,
            "current_step_index": self.current_step_index,
            "total_steps": self.total_steps,
            "step_progress": self.step_progress,
            "error": self.error,
            "progress_message": self.progress_message
        }

    def __repr__(self):
        return f"<Task(taskId={self.taskId}, status={self.status})>"