from sqlalchemy.orm import declarative_base

Base = declarative_base()

# 导入所有模型，这样 alembic 才能发现它们
from models.user import User
from models.task import Task
from models.rss import RSSFeed, RSSEntry

# 确保所有模型都在这里导入，这样 alembic 才能检测到它们
__all__ = ["Base", "User", "Task", "RSSFeed", "RSSEntry"]