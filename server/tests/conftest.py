import warnings
warnings.filterwarnings("ignore", message="'audioop' is deprecated", category=DeprecationWarning)

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# 配置 pytest-asyncio
pytest_plugins = ['pytest_asyncio']

def pytest_configure(config):
    # 注册异步测试标记
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as requiring asyncio"
    )

# 然后是其他导入
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import shutil
import tempfile

from db.base import Base
from main import app
from db.session import get_db
from core.config import settings
from models.task import Task
from models.user import User
from models.enums import TaskStatus, TaskProgress
from utils.time_utils import TimeUtil

# 使用内存数据库进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def test_user(db_session):
    from auth.utils import get_password_hash
    user = User(
        username="testuser",
        hashed_password=get_password_hash("testpass"),
        nickname="Test User"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_admin(db_session):
    from auth.utils import get_password_hash
    admin = User(
        username="admin",
        hashed_password=get_password_hash("adminpass"),
        nickname="Admin User",
        is_admin=True
    )
    db_session.add(admin)
    db_session.commit()
    return admin

@pytest.fixture
def test_task(db_session, test_user):
    current_time = TimeUtil.now_ms()
    task = Task(
        taskId="test-task-id",
        url="https://example.com/article",
        status=TaskStatus.COMPLETED.value,
        progress=TaskProgress.COMPLETED.value,
        user_id=test_user.id,
        created_by=test_user.id,
        createdAt=current_time,
        updatedAt=current_time
    )
    db_session.add(task)
    db_session.commit()
    
    task_dir = os.path.join(settings.TASK_DIR, task.taskId)
    os.makedirs(task_dir, exist_ok=True)
    
    yield task
    
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir)

@pytest.fixture
def test_users(db_session):
    from auth.utils import get_password_hash
    users = []
    for i in range(5):  # 创建5个用户
        user = User(
            username=f"testuser{i}",
            hashed_password=get_password_hash("testpass"),
            nickname=f"Test User {i}"
        )
        db_session.add(user)
        users.append(user)
    db_session.commit()
    return users

@pytest.fixture
def test_tasks(db_session, test_users):
    tasks = []
    for i, user in enumerate(test_users):
        task = Task(
            taskId=f"test-task-id-{i}",
            url=f"https://example.com/article{i}",
            status=TaskStatus.COMPLETED.value,
            progress=TaskProgress.COMPLETED.value,
            user_id=user.id,
            created_by=user.id,
            createdAt=TimeUtil.now_ms(),
            updatedAt=TimeUtil.now_ms()
        )
        db_session.add(task)
        tasks.append(task)
        
        # 创建任务文件夹和相关文件
        task_dir = os.path.join(settings.TASK_DIR, task.taskId)
        os.makedirs(task_dir, exist_ok=True)
    
    db_session.commit()
    
    yield tasks
    
    # 清理测试文件
    for task in tasks:
        task_dir = os.path.join(settings.TASK_DIR, task.taskId)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)

@pytest.fixture(autouse=True)
def test_settings():
    """为测试环境设置临时任务目录"""
    # 保存原始设置
    original_task_dir = settings.TASK_DIR
    
    # 创建临时目录作为测试任务目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 修改设置
        settings.TASK_DIR = temp_dir
        yield
        # 测试结束后恢复原始设置
        settings.TASK_DIR = original_task_dir
