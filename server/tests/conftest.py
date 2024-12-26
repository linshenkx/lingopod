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
def override_get_db(db_session):
    """覆盖get_db依赖，确保所有代码使用相同的测试数据库会话"""
    def _get_test_db():
        try:
            yield db_session
        finally:
            pass
    return _get_test_db

@pytest.fixture
def client(db_session, override_get_db):
    """创建测试客户端，并覆盖数据库依赖"""
    from db.session import get_db
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

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
def test_task(test_user, db_session):
    """创建测试任务"""
    task = Task(
        taskId="test-task",
        url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
        status=TaskStatus.COMPLETED.value,
        progress=TaskProgress.COMPLETED.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=True,
        created_at=TimeUtil.now_ms(),
        updated_at=TimeUtil.now_ms(),
        current_step="任务已完成",
        style_params={
            "content_length": "medium",
            "tone": "casual",
            "emotion": "neutral"
        }
    )
    db_session.add(task)
    db_session.commit()
    
    # 创建任务文件夹
    task_dir = os.path.join(settings.TASK_DIR, task.taskId)
    os.makedirs(task_dir, exist_ok=True)
    
    return task

@pytest.fixture
def test_tasks(test_user, db_session):
    """创建多个测试任务"""
    tasks = []
    for i in range(5):
        task = Task(
            taskId=f"test-task-{i}",
            url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
            status=TaskStatus.COMPLETED.value,
            progress=TaskProgress.COMPLETED.value,
            user_id=test_user.id,
            created_by=test_user.id,
            updated_by=test_user.id,
            is_public=True,
            created_at=TimeUtil.now_ms(),
            updated_at=TimeUtil.now_ms()
        )
        tasks.append(task)
    
    db_session.add_all(tasks)
    db_session.commit()
    return tasks

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
def mock_execute_task(monkeypatch, db_session):
    """Mock execute_task to use test database session"""
    from services.task.task_service import execute_task
    
    def mock_task_execution(task_id: str, is_retry: bool = False):
        return execute_task(task_id, is_retry, db_session=db_session)
    
    # 替换原始的execute_task函数
    monkeypatch.setattr("services.task.task_service.execute_task", mock_task_execution)
    return mock_task_execution

@pytest.fixture(autouse=True)
def setup_task_execution(mock_execute_task):
    """自动使用mock的任务执行函数"""
    pass

@pytest.fixture(autouse=True)
def test_settings():
    """为测试环境设置临时任务目录"""
    # 保存原始设置
    original_task_dir = settings.TASK_DIR
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    settings.TASK_DIR = temp_dir
    
    try:
        yield
    finally:
        # 确保所有文件句柄都关闭
        try:
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    try:
                        os.chmod(os.path.join(root, name), 0o666)
                    except:
                        pass
                for name in dirs:
                    try:
                        os.chmod(os.path.join(root, name), 0o777)
                    except:
                        pass
            
            # 尝试删除临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp directory {temp_dir}: {str(e)}")
        finally:
            # 恢复原始设置
            settings.TASK_DIR = original_task_dir
