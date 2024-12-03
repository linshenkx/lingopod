import os

from fastapi import status

from core.config import settings
from models.task import Task
from models.enums import TaskStatus, TaskProgress
from utils.time_utils import TimeUtil

def test_create_task(client, test_user):
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
        json={
            "url": "https://example.com/article",
            "is_public": True
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == TaskStatus.PROCESSING.value
    assert data["progress"] == TaskProgress.PROCESSING.value
    
    # 验证任务文件夹创建
    task_id = data["taskId"]
    task_dir = os.path.join(settings.TASK_DIR, task_id)
    assert os.path.exists(task_dir)

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
    # 先登录获取token
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
    assert isinstance(data["items"], list)
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
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
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
    # 创建另一个用户的私有任务
    other_task = Task(
        taskId="other-task-id",
        url="https://example.com/private",
        status=TaskStatus.COMPLETED.value,
        progress=TaskProgress.COMPLETED.value,
        user_id=test_user.id + 1,
        created_by=test_user.id + 1,
        is_public=False
    )
    db_session.add(other_task)
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
    
    # 验证响应
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    task_ids = [task["taskId"] for task in data["items"]]
    assert "other-task-id" not in task_ids  # 验证私有任务不可见

def test_get_task_processing_status(client, test_user, db_session):
    """测试获取处理中任务的状态"""
    # 创建处理中的任务
    task = Task(
        taskId="processing-task-id",
        url="https://example.com/article",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id
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
    
    # 记录创建前的时间
    before_create = TimeUtil.now_ms()
    
    # 创建任务
    response = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "url": "https://example.com/article",
            "is_public": True
        }
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    
    # 验证创建时间
    assert data["createdAt"] >= before_create
    assert data["updatedAt"] >= before_create
    assert data["createdAt"] == data["updatedAt"]

def test_retry_failed_task(client, test_user, db_session):
    """测试重试失败的任务"""
    # 创建一个失败的任务
    task = Task(
        taskId="failed-task-id",
        url="https://example.com/article",
        status=TaskStatus.FAILED.value,
        progress=TaskProgress.FAILED.value,
        current_step="生成对话内容",
        user_id=test_user.id,
        created_by=test_user.id
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
    assert "Task retry started" in data["message"]
    
    # 验证任务状态已更新
    task = db_session.query(Task).filter(Task.taskId == task.taskId).first()
    assert task.status == TaskStatus.PROCESSING.value
    assert task.progress == TaskProgress.WAITING.value

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
        "title": "新标题",
        "is_public": True
    }
    response = client.patch(
        f"/api/v1/tasks/{test_task.taskId}",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["is_public"] == update_data["is_public"]

def test_update_task_no_permission(client, test_user, test_admin, db_session):
    """测试无权限更新任务"""
    # 创建管理员的任务
    task = Task(
        taskId="admin-task-id",
        url="https://example.com/article",
        status=TaskStatus.COMPLETED.value,
        progress=TaskProgress.COMPLETED.value,
        user_id=test_admin.id,
        created_by=test_admin.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    # 普通用户登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 尝试更新管理员的任务
    update_data = {
        "title": "新标题",
        "is_public": True
    }
    response = client.patch(
        f"/api/v1/tasks/{task.taskId}",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    
    assert response.status_code == 403

def test_list_tasks_with_keyword_search(client, test_user, db_session):
    """测试任务列表关键词搜索"""
    # 创建测试任务
    tasks = [
        Task(
            taskId=f"task-{i}",
            url=f"https://example{i}.com/article",
            title=f"测试任务{i}",
            status=TaskStatus.COMPLETED.value,
            progress=TaskProgress.COMPLETED.value,
            user_id=test_user.id,
            created_by=test_user.id,
            is_public=True
        ) for i in range(3)
    ]
    for task in tasks:
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
    
    # 测试标题搜索
    response = client.get(
        "/api/v1/tasks?title_keyword=测试任务1",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert "测试任务1" in data["items"][0]["title"]
    
    # 测试URL搜索
    response = client.get(
        "/api/v1/tasks?url_keyword=example2",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert "example2" in data["items"][0]["url"]
    
    # 测试组合搜索
    response = client.get(
        "/api/v1/tasks?title_keyword=测试&url_keyword=example1",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert "测试" in data["items"][0]["title"]
    assert "example1" in data["items"][0]["url"]
