from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
import asyncio
import uuid
import aiohttp
import feedparser
import sqlalchemy.exc

from db.session import get_db, SessionLocal
from models.user import User
from models.rss import RSSFeed, RSSEntry
from models.task import Task
from models.enums import TaskStatus, TaskProgress
from schemas.rss import (
    RSSFeedCreate,
    RSSFeedUpdate,
    RSSFeedResponse,
    RSSFeedList,
    RSSEntryResponse
)
from auth.dependencies import get_current_user
from services.rss.feed_manager import FeedManager
from services.task.processor import TaskProcessor
from core.logging import log

router = APIRouter()

@router.get("/feeds", response_model=List[RSSFeedList])
async def list_feeds(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取RSS源列表"""
    feeds = (
        db.query(RSSFeed)
        .filter_by(user_id=current_user.id)
        .order_by(desc(RSSFeed.id))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return feeds

@router.get("/feeds/{feed_id}", response_model=RSSFeedResponse)
async def get_feed(
    feed_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取RSS源详情"""
    feed = db.get(RSSFeed, feed_id)
    if not feed or feed.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="RSS源不存在")
    return feed

@router.post("/feeds", response_model=RSSFeedResponse)
async def create_feed(
    feed: RSSFeedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建新的RSS源"""
    # 检查是否已存在相同的RSS源
    exists = db.query(RSSFeed).filter_by(
        user_id=current_user.id,
        url=str(feed.url)
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="该RSS源已存在")
    
    # 如果用户没有指定标题，则从RSS源获取
    title = feed.title
    if title is None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(feed.url)) as response:
                    content = await response.text()
                    parsed = feedparser.parse(content)
                    
            # 从RSS源获取标题
            title = parsed.feed.get('title', str(feed.url))
        except Exception as e:
            log.error(f"获取RSS源标题失败: {str(e)}")
            title = str(feed.url)  # 如果获取失败，使用URL字符串作为标题
    
    try:
        # 创建新的RSS源
        feed_data = feed.model_dump(exclude_unset=True)
        feed_data['title'] = title
        feed_data['user_id'] = current_user.id
        feed_data['url'] = str(feed.url)  # 确保 URL 被转换为字符串
        
        new_feed = RSSFeed(**feed_data)
        db.add(new_feed)
        db.commit()
        db.refresh(new_feed)
        
        # 创建一个独立的后台任务来处理RSS源
        async def background_fetch():
            try:
                async_db = SessionLocal()
                try:
                    manager = FeedManager(async_db, None)
                    await manager.fetch_feed(new_feed)
                except Exception as e:
                    log.error(f"RSS源初始化抓取失败: {str(e)}")
                finally:
                    async_db.close()
            except Exception as e:
                log.error(f"后台任务执行失败: {str(e)}")
        
        # 启动后台任务
        asyncio.create_task(background_fetch())
        
        return new_feed
    except sqlalchemy.exc.IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="该RSS源已存在")

@router.put("/feeds/{feed_id}", response_model=RSSFeedResponse)
async def update_feed(
    feed_id: int,
    feed_update: RSSFeedUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新RSS源配置"""
    feed = db.get(RSSFeed, feed_id)
    if not feed or feed.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="RSS源不存在")
    
    # 更新字段
    for field, value in feed_update.model_dump(exclude_unset=True).items():
        setattr(feed, field, value)
    
    db.commit()
    db.refresh(feed)
    return feed

@router.delete("/feeds/{feed_id}")
async def delete_feed(
    feed_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除RSS源"""
    feed = db.get(RSSFeed, feed_id)
    if not feed or feed.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="RSS源不存在")
    
    # 删除相关的条目
    db.query(RSSEntry).filter_by(feed_id=feed_id).delete()
    db.delete(feed)
    db.commit()
    
    return {"message": "RSS源已删除"}

@router.post("/feeds/{feed_id}/fetch")
async def fetch_feed(
    feed_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动获取RSS源更新"""
    feed = db.get(RSSFeed, feed_id)
    if not feed or feed.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="RSS源不存在")
    
    manager = FeedManager(db, None)  # 不需要传递 TaskProcessor
    try:
        await manager.fetch_feed(feed)
        return {"message": "RSS源更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RSS源更新失败: {str(e)}")

@router.get("/feeds/{feed_id}/entries", response_model=List[RSSEntryResponse])
async def list_feed_entries(
    feed_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取RSS源的条目列表"""
    feed = db.get(RSSFeed, feed_id)
    if not feed or feed.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="RSS源不存在")
    
    entries = (
        db.query(RSSEntry)
        .filter_by(feed_id=feed_id)
        .order_by(desc(RSSEntry.published))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries
