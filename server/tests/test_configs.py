import pytest
from fastapi import status
from core.config import config_manager, Settings

@pytest.fixture
def admin_token(client, test_admin):
    """获取管理员token"""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "adminpass"
        }
    )
    return response.json()["access_token"]

@pytest.fixture
def user_token(client, test_user):
    """获取普通用户token"""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    return response.json()["access_token"]

def test_get_all_configs(client, admin_token, user_token):
    """测试获取所有配置"""
    # 普通用户无权限访问
    response = client.get(
        "/api/v1/configs",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 管理员可以访问
    response = client.get(
        "/api/v1/configs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # 验证返回的是ConfigListResponse格式
    assert "configs" in data
    configs = data["configs"]
    # 验证只包含允许的配置项
    assert all(key in config_manager.MUTABLE_CONFIGS for key in configs.keys())
    # 验证每个配置项的格式
    for config in configs.values():
        assert "key" in config
        assert "value" in config
        assert "type" in config
        assert "description" in config

def test_update_config(client, admin_token, user_token, db_session):
    """测试更新配置"""
    test_config = {
        "value": "test-api-key",
        "type": "str",
        "description": "测试API密钥"
    }

    # 普通用户无权限更新
    response = client.put(
        "/api/v1/configs/API_KEY",
        headers={"Authorization": f"Bearer {user_token}"},
        json=test_config
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 管理员可以更新
    response = client.put(
        "/api/v1/configs/API_KEY",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=test_config
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 验证配置已更新
    response = client.get(
        "/api/v1/configs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    config = data["configs"]["API_KEY"]
    assert config["value"] == "test-api-key"
    assert config["type"] == "str"
    assert config["description"] == "测试API密钥"

def test_reset_config(client, admin_token, user_token, db_session):
    """测试重置配置"""
    # 先更新一个配置
    test_config = {
        "value": "test-api-key",
        "type": "str",
        "description": "测试API密钥"
    }
    client.put(
        "/api/v1/configs/API_KEY",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=test_config
    )

    # 普通用户无权限重置
    response = client.delete(
        "/api/v1/configs/API_KEY",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # 管理员可以重置
    response = client.delete(
        "/api/v1/configs/API_KEY",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_200_OK

    # 验证配置已重置为默认值
    response = client.get(
        "/api/v1/configs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    data = response.json()
    config = data["configs"]["API_KEY"]
    assert config["value"] == Settings().API_KEY

def test_update_invalid_config(client, admin_token):
    """测试更新无效的配置项"""
    test_config = {
        "value": "test",
        "type": "str",
        "description": "测试"
    }
    
    # 测试更新不存在的配置
    response = client.put(
        "/api/v1/configs/INVALID_KEY",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=test_config
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # 测试更新不允许修改的配置
    response = client.put(
        "/api/v1/configs/JWT_SECRET_KEY",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=test_config
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_reset_nonexistent_config(client, admin_token):
    """测试重置不存在的配置"""
    response = client.delete(
        "/api/v1/configs/NONEXISTENT_KEY",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
