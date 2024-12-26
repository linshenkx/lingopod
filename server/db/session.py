import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import settings
from auth.utils import get_password_hash
from models.user import User
import alembic.config
import os

SQLALCHEMY_DATABASE_URL = f"sqlite:///{settings.DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from db.base import Base
    
    # 创建数据库目录
    db_dir = os.path.dirname(settings.DB_PATH)
    os.makedirs(db_dir, exist_ok=True)
    
    # 创建初始表结构
    Base.metadata.create_all(bind=engine)
    
    # 创建初始管理员用户
    db = SessionLocal()
    try:
        # 检查是否已存在管理员用户
        admin = db.query(User).filter(User.is_admin == True).first()
        if not admin:
            admin_user = User(
                username=settings.ADMIN_USERNAME,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                nickname="管理员",
                is_admin=True,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logging.info("已创建初始管理员用户")
    except Exception as e:
        logging.error(f"创建管理员用户时出错: {str(e)}")
        raise
    finally:
        db.close()