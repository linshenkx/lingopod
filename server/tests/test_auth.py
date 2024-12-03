from fastapi import status
from models.user import User
from utils.time_utils import TimeUtil

def test_register_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "password": "password123",
            "nickname": "New User"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "newuser"
    assert "password" not in data

def test_login_user(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_current_user(client, test_user):
    # 先登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 用token获取当前用户信息
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "testuser"

def test_register_duplicate_username(client, test_user):
    """测试注册重复用户名"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",  # 使用已存在的用户名
            "password": "password123",
            "nickname": "Test User"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "用户名已存在" in data["detail"]

def test_login_wrong_password(client, test_user):
    """测试错误密码登录"""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "wrongpass"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "用户名或密码错误" in data["detail"]

def test_login_nonexistent_user(client):
    """测试不存在的用户登录"""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "nonexistent",
            "password": "testpass"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user_invalid_token(client):
    """测试无效token访问当前用户信息"""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user_no_token(client):
    """测试未提供token访问当前用户信息"""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user_inactive(client, test_user, db_session):
    """测试已禁用用户访问"""
    # 先登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 禁用用户
    test_user.is_active = False
    db_session.commit()
    
    # 尝试访问用户信息
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "用户已被禁用" in response.json()["detail"]

def test_registration_closed(client, monkeypatch):
    """测试关闭注册功能"""
    # 修改配置，关闭注册功能
    monkeypatch.setattr("core.config.settings.ALLOW_REGISTRATION", False)
    
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "password": "password123",
            "nickname": "New User"
        }
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "注册功能已关闭" in response.json()["detail"]

def test_login_disabled_user(client, test_user, db_session):
    """测试禁用用户登录"""
    # 禁用用户
    test_user.is_active = False
    db_session.commit()
    
    # 尝试登录
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "用户已被禁用" in response.json()["detail"]

def test_login_enabled_user(client, test_user, db_session):
    """测试启用用户登录"""
    # 启用用户
    test_user.is_active = True
    db_session.commit()
    
    # 尝试登录
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()

def test_login_updates_last_login(client, test_user, db_session):
    """测试登录时更新最近登录时间"""
    # 记录登录前的时间
    before_login = TimeUtil.now_ms()
    
    # 登录
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 验证最近登录时间已更新
    db_session.refresh(test_user)
    assert test_user.last_login is not None
    assert test_user.last_login >= before_login

def test_user_created_at_is_set(client, db_session):
    """测试创建用户时设置创建时间"""
    before_create = TimeUtil.now_ms()
    
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "password": "password123",
            "nickname": "New User"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    
    user = db_session.query(User).filter(User.username == "newuser").first()
    assert user.created_at is not None
    assert user.created_at >= before_create
