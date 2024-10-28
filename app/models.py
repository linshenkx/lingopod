from sqlalchemy import create_engine, Column, String, JSON, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import os

from app.config import CONFIG

# SQLAlchemy配置
SQLALCHEMY_DATABASE_URL = f"sqlite:///{CONFIG['DB_PATH']}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy模型
class TaskModel(Base):
    __tablename__ = "tasks"

    taskId = Column(String, primary_key=True, index=True)
    url = Column(String, nullable=False)
    status = Column(String, nullable=False)  # pending, processing, completed, failed
    progress = Column(String, nullable=False)  # 详细的进度信息
    createdAt = Column(DateTime, default=datetime.now)
    updatedAt = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    audioUrl = Column(String, nullable=True)
    title = Column(String, nullable=True)
    dialogue = Column(JSON, nullable=True)
    current_step = Column(String, nullable=True)  # 当前处理步骤
    total_steps = Column(Integer, nullable=True)  # 总步骤数
    step_progress = Column(Integer, nullable=True)  # 当前步骤进度(百分比)
    audioUrlCn = Column(String, nullable=True)  # 新增：中文音频URL
    audioUrlEn = Column(String, nullable=True)  # 新增：英文音频URL
    subtitleUrlCn = Column(String, nullable=True)  # 新增：中文字幕URL
    subtitleUrlEn = Column(String, nullable=True)  # 新增：英文字幕URL

# Pydantic模型
class TaskCreate(BaseModel):
    url: str

class Task(BaseModel):
    taskId: str
    url: str
    status: str
    progress: str
    createdAt: datetime
    updatedAt: datetime
    audioUrl: Optional[str] = None
    title: Optional[str] = None
    dialogue: Optional[List[dict]] = None
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    step_progress: Optional[int] = None
    audioUrlCn: Optional[str] = None
    audioUrlEn: Optional[str] = None
    subtitleUrlCn: Optional[str] = None
    subtitleUrlEn: Optional[str] = None

    class Config:
        from_attributes = True

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 创建数据库表
def init_db():
    # 确保数据库文件所在目录存在
    db_dir = os.path.dirname(CONFIG['DB_PATH'])
    os.makedirs(db_dir, exist_ok=True)
    
    Base.metadata.create_all(bind=engine)
