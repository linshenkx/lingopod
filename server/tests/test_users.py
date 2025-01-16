import os

from fastapi import status

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
        "email": "newemail@example.com"
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

def test_test_user_login_with_test_password(client, db_session):
    """测试test用户使用test密码登录的特殊处理"""
    # 确保启用test用户特殊处理
    assert settings.TEST_USER_ENABLED == True
    
    # 使用test/test登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.TEST_USERNAME,
            "password": settings.TEST_PASSWORD
        }
    )
    
    # 验证登录成功
    assert login_response.status_code == status.HTTP_200_OK
    assert "access_token" in login_response.json()
    
    # 验证test用户已在数据库中创建
    user = db_session.query(User).filter(User.username == settings.TEST_USERNAME).first()
    assert user is not None
    assert user.username == settings.TEST_USERNAME
    assert user.is_active == True

def test_test_user_login_after_password_change(client, db_session):
    """测试test用户修改密码后仍可使用test密码登录"""
    # 先使用test密码登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.TEST_USERNAME,
            "password": settings.TEST_PASSWORD
        }
    )
    token = login_response.json()["access_token"]
    
    # 修改密码
    new_password = "newpassword123"
    response = client.post(
        "/api/v1/users/me/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": settings.TEST_PASSWORD,
            "new_password": new_password
        }
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 验证新密码可以登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.TEST_USERNAME,
            "password": new_password
        }
    )
    assert login_response.status_code == status.HTTP_200_OK
    
    # 验证test密码仍然可以登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.TEST_USERNAME,
            "password": settings.TEST_PASSWORD
        }
    )
    assert login_response.status_code == status.HTTP_200_OK

def test_test_user_login_when_disabled(client, db_session):
    """测试禁用test用户特殊处理后的登录行为"""
    # 禁用test用户特殊处理
    settings.update_config(
        db=db_session,
        key="TEST_USER_ENABLED",
        value=False,
        type_name="bool",
        description="是否启用test用户特殊处理"
    )
    
    # 尝试使用test密码登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": settings.TEST_USERNAME,
            "password": settings.TEST_PASSWORD
        }
    )
    
    # 验证登录失败（因为特殊处理被禁用）
    assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # 恢复test用户特殊处理
    settings.update_config(
        db=db_session,
        key="TEST_USER_ENABLED",
        value=True,
        type_name="bool",
        description="是否启用test用户特殊处理"
    )

def test_test_user_config_update(client, test_admin, db_session):
    """测试更新test用户配置"""
    # 使用管理员登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "adminpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 更新test用户配置
    new_test_username = "testuser2"
    response = client.put(
        "/api/v1/configs/TEST_USERNAME",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "value": new_test_username,
            "type": "str",
            "description": "测试用户名"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 验证新的test用户名可以登录
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": new_test_username,
            "password": settings.TEST_PASSWORD
        }
    )
    assert login_response.status_code == status.HTTP_200_OK

def test_update_user_me(client, test_user):
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
        "nickname": "New Nickname",
        "email": "new.email@example.com"
    }
    response = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json=update_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == update_data["nickname"]
    assert data["email"] == update_data["email"]
