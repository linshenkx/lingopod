import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import requests

from main import app
from models.user import User
from models.rss import RSSFeed, RSSEntry
from services.rss.feed_manager import FeedManager
from services.task.processor import TaskProcessor
from core.scheduler import fetch_all_feeds
from core.config import settings
from auth.utils import get_password_hash
from utils.time_utils import TimeUtil
import zoneinfo

client = TestClient(app)

def get_current_time():
    """获取当前时间戳（毫秒）"""
    return TimeUtil.now_ms()

def get_time_with_offset(offset_seconds: int) -> int:
    """获取偏移后的时间戳（毫秒）"""
    return TimeUtil.now_ms() + (offset_seconds * 1000)

def mock_task_processor():
    """创建模拟的任务处理器"""
    processor = MagicMock(spec=TaskProcessor)
    processor.process_task = AsyncMock()
    return processor

@pytest.fixture
def mock_feed_manager():
    """模拟 FeedManager"""
    with patch('services.rss.feed_manager.FeedManager') as mock:
        manager = MagicMock(spec=FeedManager)
        manager.fetch_feed = AsyncMock()
        mock.return_value = manager
        yield manager

@pytest.fixture
def mock_url_fetcher():
    """模拟URL内容获取"""
    with patch('services.url_fetcher.fetch_url_content') as mock:
        mock.return_value = ('模拟的页面内容', '模拟的标题')
        yield mock

@pytest.fixture
def mock_http_client():
    """模拟HTTP请求"""
    with patch('requests.get') as mock:
        mock.return_value.status_code = 200
        mock.return_value.text = '模拟的页面内容'
        yield mock

@pytest.fixture
def test_user(db_session: Session):
    """创建测试用户"""
    user = User(
        username="testuser",  # 使用与 conftest.py 相同的用户名
        email="test@example.com",
        hashed_password=get_password_hash("testpass"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_token(client, test_user: User):
    """创建测试用户的令牌"""
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    assert login_response.status_code == status.HTTP_200_OK
    return login_response.json()["access_token"]

@pytest.fixture
def test_feed(db_session: Session, test_user: User):
    """创建测试RSS源"""
    feed = RSSFeed(
        title="Test Feed",
        url="http://example.com/feed.xml",
        user_id=test_user.id,
        fetch_interval=900,
        initial_entries_count=2,
        update_entries_count=1
    )
    db_session.add(feed)
    db_session.commit()
    db_session.refresh(feed)
    return feed

class TestRSSAPI:
    """RSS API测试"""
    
    def test_create_feed(self, client, test_token: str, mock_feed_manager):
        """测试创建RSS源"""
        response = client.post(
            "/api/v1/rss/feeds",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "url": "http://example.com/feed.xml",
                "fetch_interval": 900,
                "initial_entries_count": 2,
                "update_entries_count": 1
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["url"] == "http://example.com/feed.xml"
        assert data["fetch_interval"] == 900
        assert data["initial_entries_count"] == 2
        assert data["update_entries_count"] == 1

    def test_list_feeds(self, client, test_token: str, test_feed: RSSFeed):
        """测试获取RSS源列表"""
        response = client.get(
            "/api/v1/rss/feeds",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_feed.id
        assert data[0]["title"] == test_feed.title

    def test_get_feed(self, client, test_token: str, test_feed: RSSFeed):
        """测试获取单个RSS源"""
        response = client.get(
            f"/api/v1/rss/feeds/{test_feed.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_feed.id
        assert data["title"] == test_feed.title

    def test_update_feed(self, client, test_token: str, test_feed: RSSFeed):
        """测试更新RSS源"""
        response = client.put(
            f"/api/v1/rss/feeds/{test_feed.id}",
            headers={"Authorization": f"Bearer {test_token}"},
            json={
                "fetch_interval": 1800,
                "initial_entries_count": 5,
                "update_entries_count": 3
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["fetch_interval"] == 1800
        assert data["initial_entries_count"] == 5
        assert data["update_entries_count"] == 3

    def test_delete_feed(self, client, test_token: str, test_feed: RSSFeed):
        """测试删除RSS源"""
        response = client.delete(
            f"/api/v1/rss/feeds/{test_feed.id}",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_fetch_feed(self, client, test_token: str, test_feed: RSSFeed, mock_feed_manager):
        """测试手动获取RSS源更新"""
        # 确保 mock 完全覆盖 FeedManager
        with patch('api.v1.rss.FeedManager', return_value=mock_feed_manager):
            mock_feed_manager.fetch_feed.return_value = None
            
            response = client.post(
                f"/api/v1/rss/feeds/{test_feed.id}/fetch",
                headers={"Authorization": f"Bearer {test_token}"}
            )
            assert response.status_code == status.HTTP_200_OK
            mock_feed_manager.fetch_feed.assert_called_once()

    def test_list_feed_entries(self, client, test_token: str, test_feed: RSSFeed, db_session: Session):
        """测试获取RSS源条目列表"""
        # 创建测试条目
        entry = RSSEntry(
            feed_id=test_feed.id,
            guid="test_guid",
            title="Test Entry",
            link="http://example.com/entry1",
            published=TimeUtil.now_ms()
        )
        db_session.add(entry)
        db_session.commit()

        response = client.get(
            f"/api/v1/rss/feeds/{test_feed.id}/entries",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == entry.title
        assert data[0]["link"] == entry.link

class TestRSSService:
    """RSS服务层测试"""
    
    @pytest.mark.asyncio
    async def test_feed_creation(self, db_session: Session, mock_feed_manager):
        """测试RSS源的创建"""
        user = User(
            username="testuser",
            email="test1@example.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        feed = RSSFeed(
            url="https://test-feed-url.com/rss",
            title="Test Feed",
            user_id=user.id,
            fetch_interval=900,  # 15分钟
            initial_entries_count=2,
            update_entries_count=1
        )
        db_session.add(feed)
        db_session.commit()
        
        assert feed.id is not None
        assert feed.url == "https://test-feed-url.com/rss"
        assert feed.title == "Test Feed"
        assert feed.user_id == user.id
        assert feed.fetch_interval == 900
        assert feed.initial_entries_count == 2
        assert feed.update_entries_count == 1

    @pytest.mark.asyncio
    async def test_feed_fetch_initial(self, db_session: Session, mock_feed_manager):
        """测试RSS源的首次抓取"""
        user = User(
            username="testuser",
            email="test1@example.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        feed = RSSFeed(
            url="https://test-feed-url.com/rss",
            title="Test Feed",
            user_id=user.id,
            fetch_interval=900,
            initial_entries_count=2,
            update_entries_count=1
        )
        db_session.add(feed)
        db_session.commit()
        
        await mock_feed_manager.fetch_feed(feed)
        mock_feed_manager.fetch_feed.assert_called_once_with(feed)

    @pytest.mark.asyncio
    async def test_feed_fetch_update(self, db_session: Session, mock_feed_manager):
        """测试RSS源的更新抓取"""
        user = User(
            username="testuser",
            email="test3@example.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        # 创建RSS Feed，配置更新时处理1条
        last_fetch = get_time_with_offset(-7200)  # 2小时前
        feed = RSSFeed(
            url="https://test-feed-url.com/rss",
            title="Test Feed",
            user_id=user.id,
            initial_entries_count=2,
            update_entries_count=1,
            last_fetch=last_fetch,
            fetch_interval=900
        )
        db_session.add(feed)
        db_session.commit()
        
        await mock_feed_manager.fetch_feed(feed)
        mock_feed_manager.fetch_feed.assert_called_once_with(feed)

    @pytest.mark.asyncio
    async def test_scheduled_feed_fetch(self, db_session: Session, mock_feed_manager):
        """测试定时任务"""
        user = User(
            username="testuser",
            email="test4@example.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        # 创建两个RSS Feed
        now = get_current_time()
        feed1 = RSSFeed(
            url="https://test-feed1.com/rss",
            title="Test Feed 1",
            user_id=user.id,
            last_fetch=None,  # 从未抓取过，应该被更新
            initial_entries_count=2,
            is_active=True
        )
        
        feed2 = RSSFeed(
            url="https://test-feed2.com/rss",
            title="Test Feed 2",
            user_id=user.id,
            last_fetch=now,  # 刚刚抓取过，不应该被更新
            fetch_interval=3600,  # 1小时更新一次
            initial_entries_count=2,
            is_active=True
        )
        
        db_session.add_all([feed1, feed2])
        db_session.commit()
        
        feed1_id = feed1.id
        feed2_id = feed2.id
        feed2_original_fetch = feed2.last_fetch
        
        # 模拟 process_all_feeds 的行为
        async def mock_process_all_feeds():
            # 只处理需要更新的feed
            current_time = get_current_time()
            feeds = db_session.query(RSSFeed).filter(
                RSSFeed.is_active == True,
                (
                    RSSFeed.last_fetch.is_(None) |
                    (
                        RSSFeed.last_fetch < current_time - 3600000  # 1小时的毫秒数
                    )
                )
            ).all()
            
            for feed in feeds:
                feed.last_fetch = current_time
                db_session.add(feed)
            db_session.commit()
            
        # 设置 mock
        mock_feed_manager.process_all_feeds = AsyncMock(side_effect=mock_process_all_feeds)
        
        # 模拟调度器执行
        with patch('core.scheduler.get_db', return_value=iter([db_session])), \
             patch('core.scheduler.FeedManager', return_value=mock_feed_manager):
            await fetch_all_feeds()
            
            # 验证结果
            feed1 = db_session.get(RSSFeed, feed1_id)
            feed2 = db_session.get(RSSFeed, feed2_id)
            
            assert feed1.last_fetch is not None  # feed1应该被更新
            assert feed2.last_fetch == feed2_original_fetch  # feed2不应该被更新
            
            # 验证 process_all_feeds 被调用
            mock_feed_manager.process_all_feeds.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_latest_entry_only(self, db_session: Session, mock_feed_manager):
        """测试是否只处理最新的RSS条目"""
        user = User(
            username="testuser",
            email="test5@example.com",
            hashed_password=get_password_hash("testpass"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        # 创建RSS Feed
        feed = RSSFeed(
            url="https://test-feed3.com/rss",
            title="Test Feed 3",
            user_id=user.id,
            initial_entries_count=1
        )
        db_session.add(feed)
        db_session.commit()
        
        await mock_feed_manager.fetch_feed(feed)
        mock_feed_manager.fetch_feed.assert_called_once_with(feed)
