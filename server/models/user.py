from sqlalchemy import Column, String, BigInteger, Integer, Boolean
from sqlalchemy.orm import relationship
from db.base import Base
from utils.time_utils import TimeUtil

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    nickname = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(BigInteger, nullable=False, default=TimeUtil.now_ms)
    last_login = Column(BigInteger, nullable=True)
    tts_voice = Column(String, default="zh-CN-XiaoxiaoNeural")
    tts_rate = Column(Integer, default=0)
    
    tasks = relationship(
        "Task",
        back_populates="user",
        foreign_keys="[Task.user_id]"
    )