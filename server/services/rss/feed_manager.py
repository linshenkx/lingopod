import feedparser
import asyncio
import time
import uuid
from datetime import datetime
import zoneinfo
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, select, extract
from sqlalchemy.orm import Session, attributes
from sqlalchemy import desc
from models.rss import RSSFeed, RSSEntry
from models.task import Task
from models.enums import TaskStatus, TaskProgress
from core.config import settings
from services.task.processor import TaskProcessor
from core.logging import log
from utils.time_utils import TimeUtil
from db.session import SessionLocal
import logging
import aiohttp
import threading

logger = logging.getLogger(__name__)

class FeedManager:
    def __init__(self, db: Session, task_processor: TaskProcessor):
        self.db = db
        self.task_processor = task_processor
        self.timezone = zoneinfo.ZoneInfo(settings.TIMEZONE)
        
    async def fetch_feed(self, feed: RSSFeed) -> None:
        """获取并处理RSS源的内容
        
        Args:
            feed: RSS源对象
            
        Raises:
            Exception: 当获取或处理RSS内容出错时抛出
        """
        try:
            # 异步获取RSS内容
            async with aiohttp.ClientSession() as session:
                async with session.get(feed.url) as response:
                    content = await response.text()
                    parsed = feedparser.parse(content)
            
            # 检查状态码（如果存在）
            status = getattr(parsed, 'status', 200)
            if isinstance(status, int) and status >= 400:
                raise Exception(f"获取RSS内容失败: HTTP {status}")
            
            # 更新feed信息
            is_initial_fetch = feed.last_fetch is None
            current_time = TimeUtil.now_ms()
            feed.last_fetch = current_time
            feed.error_count = 0
            
            # 处理条目，按发布时间倒序排序
            entries = sorted(
                parsed.entries,
                key=lambda x: x.get('published_parsed', 0),
                reverse=True
            )
            
            # 根据是否首次抓取决定处理的条目数量
            max_entries = (
                feed.initial_entries_count if is_initial_fetch
                else feed.update_entries_count
            )
            
            # 提取所有条目的guid进行批量查重
            entry_guids = []
            entry_data = []
            
            for entry in entries[:max_entries]:
                guid = entry.get('id') or entry.get('link')
                if not guid:
                    log.warning(f"跳过无效条目: 缺少guid, feed={feed.url}")
                    continue
                entry_guids.append(guid)
                entry_data.append(entry)
            
            if not entry_guids:
                log.info(f"没有找到有效的RSS条目: {feed.url}")
                self.db.commit()
                return
                
            # 批量查询已存在的guid，同时考虑user_id
            stmt = (
                select(RSSEntry.guid)
                .where(
                    RSSEntry.guid.in_(entry_guids),
                    RSSEntry.user_id == feed.user_id
                )
            )
            existing_guids = set(row[0] for row in self.db.execute(stmt).fetchall())
            
            # 批量处理新条目
            new_entries = []
            new_tasks = []
            
            for entry in entry_data:
                guid = entry.get('id') or entry.get('link')
                
                # 跳过已存在的条目
                if guid in existing_guids:
                    log.debug(f"跳过已存在的条目: {guid}")
                    continue
                
                # 处理发布时间
                published = self._parse_entry_time(entry) or current_time
                
                try:
                    # 创建RSS条目记录
                    new_entry = RSSEntry(
                        feed_id=feed.id,
                        guid=guid,
                        title=entry.get('title'),
                        link=entry.get('link'),
                        published=published,
                        user_id=feed.user_id
                    )
                    new_entries.append(new_entry)
                    
                    # 创建播客任务
                    task = Task(
                        taskId=str(uuid.uuid4()),
                        url=entry.get('link'),
                        title=entry.get('title'),
                        user_id=feed.user_id,
                        is_public=True,
                        created_by=feed.user_id,
                        status=TaskStatus.PENDING.value,
                        progress=TaskProgress.WAITING.value
                    )
                    new_tasks.append(task)
                except Exception as e:
                    log.error(f"创建条目或任务失败: {str(e)}, guid={guid}")
                    continue
            
            if new_entries:
                try:
                    # 1. 保存条目和任务
                    self.db.add_all(new_entries)
                    self.db.add_all(new_tasks)
                    self.db.flush()
                    
                    # 2. 更新关联关系
                    for entry, task in zip(new_entries, new_tasks):
                        entry.task_id = task.taskId
                    
                    # 3. 提交事务
                    self.db.commit()
                    
                    # 4. 启动任务处理 - 使用execute_task
                    from services.task.task_service import execute_task
                    for task in new_tasks:
                        # 只传递task_id，让execute_task自己创建新的数据库会话
                        threading.Thread(
                            target=execute_task,
                            args=(task.taskId, False)
                        ).start()
                    
                    log.info(f"成功处理RSS源 {feed.url}: 添加了 {len(new_entries)} 个新条目")
                except Exception as e:
                    log.error(f"保存新条目时出错: {str(e)}")
                    self.db.rollback()
                    raise
            else:
                log.info(f"RSS源 {feed.url} 没有新的条目需要处理")
                self.db.commit()
            
        except Exception as e:
            log.error(f"处理RSS源出错: {feed.url}, error={str(e)}")
            raise
            
    def _parse_entry_time(self, entry) -> int:
        """解析RSS条目的发布时间
        
        Args:
            entry: RSS条目数据
            
        Returns:
            毫秒时间戳，如果解析失败返回当前时间戳
        """
        try:
            published_parsed = entry.get('published_parsed')
            if published_parsed:
                return int(time.mktime(published_parsed) * 1000)  # 转换为毫秒时间戳
            return TimeUtil.now_ms()
        except Exception as e:
            log.warning(f"解析发布时间失败: {str(e)}")
            return TimeUtil.now_ms()
            
    async def process_all_feeds(self) -> None:
        """处理所有需要更新的RSS源"""
        try:
            # 获取所有需要更新的活跃RSS源
            current_time = TimeUtil.now_ms()
            feeds = (
                self.db.query(RSSFeed)
                .filter(RSSFeed.is_active == True)
                .filter(
                    (RSSFeed.last_fetch.is_(None)) |
                    (current_time > RSSFeed.last_fetch + RSSFeed.fetch_interval * 1000)  # 转换为毫秒
                )
                .all()
            )
            
            if not feeds:
                logger.info("没有需要更新的RSS源")
                return
                
            # 限制并发数量，避免系统负载过高
            chunk_size = 5  # 每批处理5个feeds
            for i in range(0, len(feeds), chunk_size):
                chunk = feeds[i:i + chunk_size]
                tasks = [self.fetch_feed(feed) for feed in chunk]
                await asyncio.gather(*tasks)
                
                # 在每批处理之间稍作暂停，避免过度占用资源
                if i + chunk_size < len(feeds):
                    await asyncio.sleep(1)
                    
            logger.info(f"完成所有RSS源的处理，共处理 {len(feeds)} 个源")
                
        except Exception as e:
            logger.error(f"批量处理RSS源时出错: {str(e)}")
            raise
