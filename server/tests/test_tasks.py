import os

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from core.config import settings
from models.enums import TaskStatus, TaskProgress
from models.task import Task
from schemas.task import TaskCreate, StyleParams
from utils.time_utils import TimeUtil
from utils.auth import get_password_hash
from models.user import User


def get_valid_test_url():
    """获取用于测试的有效URL"""
    return "https://mp.weixin.qq.com/s/test-article"

def get_test_task_data(url=None):
    """获取用于测试的任务数据"""
    return {
        "url": url or get_valid_test_url()
    }

def test_create_task(client, test_user, override_get_db, db_session):
    """测试创建任务"""
    # 获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 创建任务
    response = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json=get_test_task_data()
    )
    
    # 添加详细的错误信息输出
    if response.status_code != status.HTTP_201_CREATED:
        print(f"Error response: {response.status_code}")
        print(f"Response content: {response.content}")
        
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    
    # 验证任务创建成功
    db_session.rollback()  # 回滚之前的事务
    with db_session.begin():  # 使用上下文管理器自动管理事务
        task = db_session.query(Task).filter(Task.taskId == data["taskId"]).first()
        assert task is not None
        assert task.status == TaskStatus.PROCESSING.value
        assert task.created_by == test_user.id

def test_get_task(client, test_user, test_task):
    # 先登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取任务详情
    response = client.get(
        f"/api/v1/tasks/{test_task.taskId}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["taskId"] == test_task.taskId
    assert data["url"] == test_task.url

def test_list_tasks(client, test_user, test_task):
    """测试获取任务列表"""
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取任务列表
    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) > 0
    
def test_delete_task(client, test_user, test_task):
    # 先登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 删除任务
    response = client.delete(
        f"/api/v1/tasks/{test_task.taskId}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 验证任务文件夹已删除
    task_dir = os.path.join(settings.TASK_DIR, test_task.taskId)
    assert not os.path.exists(task_dir)

def test_get_task_not_found(client, test_user):
    # 先登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取不存在的任务
    response = client.get(
        "/api/v1/tasks/non-existent-id",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_unauthorized_access(client):
    # 未登录访问
    response = client.get("/api/v1/tasks")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_list_tasks_with_no_tasks(client, test_user):
    """测试空任务列表"""
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取任务列表
    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) == 0
    assert data["total"] == 0

def test_list_tasks_with_private_tasks(client, test_user, test_task, db_session):
    """测试私有任务访问权限"""
    # 创建一个私有任务
    private_task = Task(
        taskId="private-task-id",
        url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
        status=TaskStatus.COMPLETED.value,
        progress=TaskProgress.COMPLETED.value,
        user_id=test_user.id,
        created_by=test_user.id,
        created_at=TimeUtil.now_ms(),
        updated_at=TimeUtil.now_ms()
    )
    db_session.add(private_task)
    db_session.commit()
    
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取任务列表
    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # 验证私有任务可见性
    task_ids = [task["taskId"] for task in data["items"]]
    assert private_task.taskId in task_ids  # 用户可以看到自己的私有任务

def test_get_task_processing_status(client, test_user, db_session):
    """测试获取处理中任务的状态"""
    # 创建处理中的任务
    task = Task(
        taskId="processing-task-id",
        url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        created_at=TimeUtil.now_ms(),
        updated_at=TimeUtil.now_ms(),
        style_params={
            "content_length": "medium",
            "tone": "casual",
            "emotion": "neutral"
        }
    )
    db_session.add(task)
    db_session.commit()
    
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取任务详情
    response = client.get(
        f"/api/v1/tasks/{task.taskId}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == TaskStatus.PROCESSING.value

def test_get_task_forbidden(client, test_user, test_admin, db_session):
    """测试访问其他用户的私有任务"""
    # 创建私有任务
    task = Task(
        taskId="private-task-id",
        url="https://example.com/private",
        status=TaskStatus.COMPLETED.value,
        progress=TaskProgress.COMPLETED.value,
        user_id=test_admin.id,
        created_by=test_admin.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    # 使用普通用户登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 尝试访问私有任务
    response = client.get(
        f"/api/v1/tasks/{task.taskId}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_list_tasks_with_pagination(client, test_user, test_task):
    # 先登录获token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取任务列表，使用分页参数
    response = client.get(
        "/api/v1/tasks?limit=1&offset=0",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) == 1  # 验证分页返回的任务数量

def test_task_timestamps(client, test_user, db_session):
    """测试任务创建和更新时间戳"""
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 记录创建前的时间戳
    before_create = TimeUtil.now_ms()
    
    # 创建任务
    response = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json=get_test_task_data()
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    
    # 验证时间戳格式
    assert "created_at" in data
    assert "updated_at" in data
    assert isinstance(data["created_at"], int)
    assert isinstance(data["updated_at"], int)
    assert data["created_at"] >= before_create
    assert data["updated_at"] >= before_create
    # 允许1秒的误差范围
    assert abs(data["created_at"] - data["updated_at"]) <= 1000

def test_retry_failed_task(client, test_user, db_session):
    """测试重试失败的任务"""
    # 创建一个失败的任务
    task = Task(
        taskId="failed-task-id",
        url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
        status=TaskStatus.FAILED.value,
        progress=TaskProgress.FAILED.value,
        user_id=test_user.id,
        created_by=test_user.id,
        created_at=TimeUtil.now_ms(),
        updated_at=TimeUtil.now_ms(),
        current_step="任务处理失败",  # 设置初始步骤状态
        style_params={
            "content_length": "long",
            "tone": "casual",
            "emotion": "neutral"
        }
    )
    db_session.add(task)
    db_session.commit()
    
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 重试任务
    response = client.post(
        f"/api/v1/tasks/{task.taskId}/retry",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "message" in data
    assert "Task retry started" in data["message"]
    
    # 验证任务状态已更新
    task = db_session.query(Task).filter(Task.taskId == task.taskId).first()
    assert task.status == TaskStatus.PROCESSING.value
    assert task.progress == TaskProgress.WAITING.value
    
    # 获取最新的任务状态
    status_response = client.get(
        f"/api/v1/tasks/{task.taskId}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert status_response.status_code == status.HTTP_200_OK
    status_data = status_response.json()
    assert "current_step" in status_data  # 在任务详情中验证 current_step

def test_update_task(client, test_user, test_task, db_session):
    """测试更新任务"""
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 先查看当前任务状态
    task = db_session.query(Task).filter(Task.taskId == test_task.taskId).first()
    
    # 更新任务
    update_data = {
        "style_params": StyleParams(
            content_length="long",
            tone="casual",
            emotion="neutral"
        ).model_dump()
    }
    response = client.patch(
        f"/api/v1/tasks/{test_task.taskId}",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["style_params"]["content_length"] == "long"

def test_list_tasks_with_filters(client, test_user, test_tasks):
    """测试任务列表过滤功能"""
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser0",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 测试状态过滤
    response = client.get(
        "/api/v1/tasks?status=completed&limit=10&offset=0",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] > 0  # 验证有数据
    assert len(data["items"]) > 0
    assert all(task["status"] == "completed" for task in data["items"])
    
    # 测试日期过滤
    current_time = TimeUtil.now_ms()
    response = client.get(
        f"/api/v1/tasks?start_date={current_time - 86400000}&limit=10&offset=0",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] > 0

def test_list_tasks_with_keyword_search(client, test_user, db_session):
    """测试任务列表关键词搜索"""
    # 创建一些测试任务
    tasks = []
    for i in range(3):
        task = Task(
            taskId=f"test-search-task-{i}",
            url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
            status=TaskStatus.COMPLETED.value,
            progress=TaskProgress.COMPLETED.value,
            title=f"Test Title {i}",
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
    
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 使用关键词搜索
    response = client.get(
        "/api/v1/tasks?keyword=Test",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) > 0
    for item in data["items"]:
        assert "Test" in item["title"]

def test_create_task_with_valid_url(client: TestClient, db_session: Session, test_user):
    """测试使用有效的微信公众号URL创建任务"""
    # 获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]

    url = "https://mp.weixin.qq.com/s/valid-article-id"
    task_data = {
        "url": url,
        "is_public": False
    }

    response = client.post(
        "/api/v1/tasks",
        json=task_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["url"] == url

    # 验证任务是否真的创建在数据库中
    db_session.expire_all()  # 清理会话状态
    db_session.rollback()  # 回滚之前的事务
    task = db_session.query(Task).filter(Task.url == url).first()
    assert task is not None

def test_create_task_with_invalid_url(client: TestClient, db_session: Session, test_user):
    """测试使用无效URL创建任务时的错误处理"""
    # 获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    invalid_urls = [
        "https://example.com/article",  # 非微信公众号URL
        "http://mp.weixin.qq.com/s/article-id",  # 非HTTPS
        "https://other-site.com/post",  # 完全不相关的网站
        "not-a-url",  # 非URL格式
        "",  # 空URL
    ]
    
    for url in invalid_urls:
        task_data = {
            "url": url,
            "is_public": False
        }
        
        response = client.post(
            "/api/v1/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # 应该返回验证错误
        error_data = response.json()
        assert isinstance(error_data, dict)
        assert "detail" in error_data
        
        if url.startswith("https://") and "mp.weixin.qq.com" not in url:
            # URL 格式正确但不是微信链接
            assert "URL必须匹配模式" in str(error_data["detail"])
        
        # 验证没有任务被创建
        db_session.rollback()  # 回滚之前的事务
        with db_session.begin():  # 使用上下文管理器自动管理事务
            task = db_session.query(Task).filter(Task.url == url).first()
            assert task is None

def test_create_task_with_modified_url_pattern(client: TestClient, db_session: Session, test_user, monkeypatch):
    """测试修改URL模式后的任务创建"""
    # 获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]

    # 临时修改允许的URL模式
    new_pattern = r'^https://(mp\.weixin\.qq\.com|example\.com)'
    monkeypatch.setattr(settings, "ALLOWED_URL_PATTERN", new_pattern)

    # 测试新模式允许的URL
    valid_urls = [
        "https://mp.weixin.qq.com/s/article-1",
        "https://example.com/post-1"
    ]

    for url in valid_urls:
        task_data = {
            "url": url,
            "is_public": False
        }

        response = client.post(
            "/api/v1/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["url"] == url

        # 验证任务是否真的创建在数据库中
        db_session.rollback()  # 回滚之前的事务
        with db_session.begin():  # 使用上下文管理器自动管理事务
            task = db_session.query(Task).filter(Task.url == url).first()
            assert task is not None

def test_task_create_schema_validation():
    """测试TaskCreate模型的URL验证"""
    # 测试有效URL
    valid_url = "https://mp.weixin.qq.com/s/valid-id"
    task = TaskCreate(url=valid_url, is_public=False)
    assert str(task.url) == valid_url
    
    # 测试各种无效URL
    invalid_urls = [
        "https://example.com/article",  # 不匹配模式
        "not-a-url",  # 非URL格式
        "",  # 空字符串
    ]
    
    for invalid_url in invalid_urls:
        with pytest.raises(ValidationError) as exc_info:  # 只捕获 ValidationError
            TaskCreate(url=invalid_url, is_public=False)
        error_message = str(exc_info.value)
        
        if invalid_url.startswith("https://"):
            # URL 格式正确但不是微信链接
            assert "URL必须匹配模式" in error_message
        else:
            # 非 HTTPS URL 或无效 URL
            assert "URL" in error_message  # 简化错误消息检查

@pytest.mark.asyncio
async def test_create_task_error_handling(client: TestClient, db_session: Session, test_user):
    """测试创建任务时的错误处理"""
    # 获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 测试无效的JSON数据
    response = client.post(
        "/api/v1/tasks",
        json={"invalid": "data"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422  # FastAPI的验证错误
    
    # 测试缺少必需字段
    response = client.post(
        "/api/v1/tasks",
        json={"is_public": True},  # 缺少url字段
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422

def test_list_tasks_with_private_tasks(client, test_user, test_task, db_session):
    """测试私有任务访问权限"""
    # 创建一个私有任务
    private_task = Task(
        taskId="test-private-task",
        url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
        status=TaskStatus.COMPLETED.value,
        progress=TaskProgress.COMPLETED.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False,
        created_at=TimeUtil.now_ms(),
        updated_at=TimeUtil.now_ms()
    )
    db_session.add(private_task)
    db_session.commit()
    
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取任务列表
    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # 验证返回的任务列表包含私有任务
    task_ids = [task["taskId"] for task in data["items"]]
    assert private_task.taskId in task_ids

def test_list_tasks_with_pagination(client, test_user, test_task):
    """测试任务列表分页"""
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取第一页任务列表
    response = client.get(
        "/api/v1/tasks?page=1&per_page=10",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)

def test_task_timestamps(client, test_user, db_session):
    """测试任务创建和更新时间戳"""
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 记录创建前的时间戳
    before_create = TimeUtil.now_ms()
    
    # 创建任务
    response = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json=get_test_task_data()
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    
    # 验证时间戳格式
    assert "created_at" in data
    assert "updated_at" in data
    assert isinstance(data["created_at"], int)
    assert isinstance(data["updated_at"], int)
    assert data["created_at"] >= before_create
    assert data["updated_at"] >= before_create
    # 允许1秒的误差范围
    assert abs(data["created_at"] - data["updated_at"]) <= 1000

def test_list_tasks_with_filters(client, test_user, test_tasks):
    """测试任务列表过滤功能"""
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 使用不同的过滤条件获取任务列表
    filters = [
        "?status=completed",
        "?start_date=1609459200000",  # 2021-01-01
        "?end_date=1640995200000",    # 2021-12-31
        "?keyword=test"
    ]
    
    for filter_str in filters:
        response = client.get(
            f"/api/v1/tasks{filter_str}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

def test_update_task(client, test_user, test_task):
    """测试更新任务"""
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 更新任务
    update_data = {
        "is_public": True,
        "style_params": StyleParams(
            content_length="long",
            tone="formal",
            emotion="professional"
        ).model_dump()
    }
    
    response = client.patch(
        f"/api/v1/tasks/{test_task.taskId}",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["is_public"] == update_data["is_public"]
    assert data["style_params"]["content_length"] == update_data["style_params"]["content_length"]

def test_list_tasks_with_keyword_search(client, test_user, db_session):
    """测试任务列表关键词搜索"""
    # 创建一些测试任务
    tasks = []
    for i in range(3):
        task = Task(
            taskId=f"test-search-task-{i}",
            url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
            status=TaskStatus.COMPLETED.value,
            progress=TaskProgress.COMPLETED.value,
            title=f"Test Title {i}",
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
    
    # 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 使用关键词搜索
    response = client.get(
        "/api/v1/tasks?keyword=Test",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) > 0
    for item in data["items"]:
        assert "Test" in item["title"]
