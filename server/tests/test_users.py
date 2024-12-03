import pytest
from fastapi import status
import os
from core.config import settings
from models.user import User
from utils.time_utils import TimeUtil

def test_delete_user_as_admin(client, test_admin, test_user, test_task):
    # 使用管理员登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "adminpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 验证任务文件夹存在
    task_dir = os.path.join(settings.TASK_DIR, test_task.taskId)
    assert os.path.exists(task_dir)
    
    # 删除用户
    response = client.delete(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # 验证用户已删除
    response = client.get(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    
    # 验证任务文件夹已删除
    assert not os.path.exists(task_dir)

def test_delete_user_as_non_admin(client, test_user):
    # 使用普通用户登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 尝试删除用户
    response = client.delete(
        f"/api/v1/users/{test_user.id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_list_users_with_pagination(client, test_admin):
    # 使用管理员登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "adminpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取用户列表，使用分页参数
    response = client.get(
        "/api/v1/users?limit=1&offset=0",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # 验证返回结构
    assert "total" in data
    assert "items" in data
    assert isinstance(data["total"], int)
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 1  # 验证分页返回的用户数量

def test_list_users_with_filters(client, test_admin, test_user):
    # 使用管理员登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "adminpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 测试用户名过滤
    response = client.get(
        "/api/v1/users?username=test",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] > 0
    assert all("test" in user["username"].lower() for user in data["items"])
    
    # 测试状态过滤
    response = client.get(
        "/api/v1/users?is_active=true",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] > 0
    assert all(user["is_active"] for user in data["items"])
    
    # 测试日期过滤 - 使用时间戳
    start_time = TimeUtil.now_ms() - (24 * 60 * 60 * 1000)  # 24小时前
    response = client.get(
        f"/api/v1/users?start_date={start_time}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data["total"], int)
    assert isinstance(data["items"], list)

def test_update_user_status(client, test_admin, test_user):
    """测试更新用户状态"""
    # 使用管理员登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "adminpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 测试禁用用户
    response = client.patch(
        f"/api/v1/users/{test_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["is_active"] == False
    assert data["id"] == test_user.id
    
    # 测试启用用户
    response = client.patch(
        f"/api/v1/users/{test_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": True}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["is_active"] == True
    assert data["id"] == test_user.id

def test_update_user_status_as_non_admin(client, test_user):
    """测试非管理员更新用户状态"""
    # 使用普通用户登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 尝试更新用户状态
    response = client.patch(
        f"/api/v1/users/{test_user.id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_update_user_status_not_found(client, test_admin):
    """测试更新不存在的用户状态"""
    # 使用管理员登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "adminpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 尝试更新不存在的用户
    response = client.patch(
        "/api/v1/users/99999/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_list_users_with_date_filter(client, test_admin, test_users):
    """测试用户列表日期过滤"""
    # 管理员登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "adminpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 获取当前时间戳
    current_time = TimeUtil.now_ms()
    
    # 测试开始时间过滤
    start_time = current_time - (24 * 60 * 60 * 1000)  # 24小时前
    response = client.get(
        f"/api/v1/users?start_date={start_time}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] > 0
    for user in data["items"]:
        assert user["created_at"] >= start_time

def test_update_current_user(client, test_user):
    """测试更新当前用户信息"""
    # 登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 更新用户信息
    update_data = {
        "nickname": "新昵称",
        "email": "newemail@example.com",
        "tts_voice": "zh-CN-YunxiNeural",
        "tts_rate": 1
    }
    
    response = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["nickname"] == update_data["nickname"]
    assert data["email"] == update_data["email"]
    assert data["tts_voice"] == update_data["tts_voice"]
    assert data["tts_rate"] == update_data["tts_rate"]

def test_update_password(client, test_user):
    """测试修改密码"""
    # 登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 修改密码
    response = client.post(
        "/api/v1/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "testpass",
            "new_password": "newpass123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 使用新密码登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "newpass123"
        }
    )
    assert login_response.status_code == status.HTTP_200_OK

def test_update_password_wrong_old_password(client, test_user):
    """测试使用错误的旧密码修改密码"""
    # 登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 尝试修改密码
    response = client.post(
        "/api/v1/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": "wrongpass",
            "new_password": "newpass123"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "旧密码错误" in response.json()["detail"]

def test_health_check(client):
    """测试健康检查接口"""
    response = client.get("/api/v1/users/health")
    
    # 验证响应状态码为200
    assert response.status_code == status.HTTP_200_OK
    
    # 验证响应内容
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "服务正常运行"
