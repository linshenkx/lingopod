from sqlalchemy import Column, String, BigInteger, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship, validates
from urllib.parse import urlparse
from db.base import Base
from models.enums import TaskProgress, TaskStatus
from utils.time_utils import TimeUtil


class Task(Base):
    """任务模型
    
    用于存储和管理任务的执行状态、进度和相关资源。
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
    audioUrlCn = Column(String, nullable=True)  # 中文音频文件URL
    audioUrlEn = Column(String, nullable=True)  # 英文音频文件URL
    subtitleUrlCn = Column(String, nullable=True)  # 中文字幕文件URL
    subtitleUrlEn = Column(String, nullable=True)  # 英文字幕文件URL
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 所属用户ID
    is_public = Column(Boolean, nullable=False, default=False)  # 是否公开
    created_by = Column(Integer, nullable=False)  # 创建者ID
    updated_by = Column(Integer, nullable=True)  # 更新者ID
    createdAt = Column(BigInteger, nullable=False, default=TimeUtil.now_ms)  # 创建时间(毫秒时间戳)
    updatedAt = Column(BigInteger, nullable=False, default=TimeUtil.now_ms, onupdate=TimeUtil.now_ms)  # 更新时间(毫秒时间戳)
    progress_message = Column(String)  # 进度消息，用于显示当前执行状态的详细信息
    
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

    def __repr__(self):
        return f"<Task(taskId={self.taskId}, status={self.status})>"