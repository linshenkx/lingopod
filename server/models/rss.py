from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship

from db.base import Base
from utils.time_utils import TimeUtil

class RSSFeed(Base):
    __tablename__ = "rss_feeds"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, index=True)
    url = Column(String, index=True)
    description = Column(String)
    last_fetch = Column(BigInteger)
    is_active = Column(Boolean, default=True)
    error_count = Column(Integer, default=0)
    fetch_interval = Column(Integer, default=900)  # 抓取间隔（秒）
    initial_entries_count = Column(Integer, default=2)  # 首次添加时处理的条目数
    update_entries_count = Column(Integer, default=1)  # 每次更新时处理的条目数
    created_at = Column(BigInteger, nullable=False, default=TimeUtil.now_ms)
    updated_at = Column(BigInteger, nullable=False, default=TimeUtil.now_ms, onupdate=TimeUtil.now_ms)
    
    user = relationship("User", back_populates="rss_feeds")
    entries = relationship("RSSEntry", back_populates="feed", cascade="all, delete-orphan")

    # 添加用户级别的URL唯一性约束
    __table_args__ = (
        UniqueConstraint('user_id', 'url', name='uix_user_url'),
    )

class RSSEntry(Base):
    __tablename__ = "rss_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey("rss_feeds.id", ondelete="CASCADE"), nullable=False)
    guid = Column(String, nullable=False)
    title = Column(String)
    link = Column(String)
    published = Column(BigInteger)  # 毫秒时间戳
    processed = Column(Boolean, default=False)
    task_id = Column(String, ForeignKey("tasks.taskId", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(BigInteger, default=lambda: TimeUtil.now_ms())
    updated_at = Column(BigInteger, default=lambda: TimeUtil.now_ms(), onupdate=lambda: TimeUtil.now_ms())

    __table_args__ = (
        UniqueConstraint('guid', 'user_id', name='uq_rss_entries_guid_user'),
    )

    # 关系
    feed = relationship("RSSFeed", back_populates="entries")
    task = relationship("Task", back_populates="rss_entries")
