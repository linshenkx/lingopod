from sqlalchemy import Column, String, Integer, Text
from db.base import Base

class SystemConfig(Base):
    __tablename__ = 'system_config'
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
