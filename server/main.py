import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from contextlib import asynccontextmanager
import logging
import threading
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from core.exceptions import validation_exception_handler, general_exception_handler
from core.config import config_manager
from core.scheduler import setup_scheduler
from db.session import get_db, init_db
from services.task.task_service import TaskService
from api.v1.api import api_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 创建lifespan上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    # 启动时的操作
    init_db()
    
    # 确保任务目录存在
    os.makedirs(config_manager.TASK_DIR, exist_ok=True)
    
    # 加载数据库配置
    db = next(get_db())
    try:
        logging.info("正在加载数据库配置...")
        config_manager.reload_db_config(db)
        
        logging.info("正在启动任务检查线程...")
        threading.Thread(
            target=TaskService.check_incomplete_tasks,
            args=(db,),
            daemon=True
        ).start()
        
        # 启动RSS调度器
        logging.info("正在启动RSS调度器...")
        scheduler = setup_scheduler()
        scheduler.start()
        
        logging.info(f"服务器已启动 - 监听地址: {config_manager.HOST}:{config_manager.PORT}")
        yield
        
        # 关闭时的操作
        logging.info("正在关闭RSS调度器...")
        scheduler.shutdown()
        logging.info("服务器正在关闭...")
    finally:
        db.close()

# 创建FastAPI应用
app = FastAPI(
    title="LingoPod API",
    lifespan=lifespan  # 使用lifespan上下文管理器
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 包含API路由
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to LingoPod API"}