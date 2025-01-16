from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.config import settings
from core.logging import log
from db.session import get_db
from services.rss.feed_manager import FeedManager
from services.task.processor import TaskProcessor

async def fetch_all_feeds():
    """定时任务：抓取所有需要更新的RSS源"""
    try:
        # 获取数据库会话
        db = next(get_db())
        try:
            # 创建FeedManager
            manager = FeedManager(db, None)  # 不需要传递 TaskProcessor
            await manager.process_all_feeds()
        finally:
            db.close()
    except Exception as e:
        log.error(f"RSS定时任务执行出错: {e}")

def setup_scheduler():
    """设置定时任务"""
    scheduler = AsyncIOScheduler()
    
    # 添加RSS抓取任务
    scheduler.add_job(
        fetch_all_feeds,
        CronTrigger(minute="*/15"),  # 每15分钟执行一次
        id="fetch_rss_feeds",
        name="RSS Feed Fetcher",
        misfire_grace_time=300  # 允许延迟5分钟
    )
    
    return scheduler
