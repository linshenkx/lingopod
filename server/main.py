import sys
from pathlib import Path
import logging



from services.task import TaskService

sys.path.append(str(Path(__file__).parent))

import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import uvicorn
from contextlib import asynccontextmanager

from api.v1 import auth, tasks, users, configs
from core.exceptions import validation_exception_handler, general_exception_handler
from core.config import config_manager
from db.session import get_db, init_db

# 在文件顶部添加测试日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    
    # 加载数据库配置
    db = next(get_db())
    try:
        logging.info("正在加载数据库配置...")
        config_manager.reload_db_config(db)
        
        logging.info("正在启动任务检查线程...")
        threading.Thread(
            target=TaskService.check_incomplete_tasks(db),
            daemon=True
        ).start()
    finally:
        db.close()
    
    logging.info(f"服务器已启动 - 监听地址: {config_manager.HOST}:{config_manager.PORT}")
    yield
    
    logging.info("服务器正在关闭...")

app = FastAPI(
    title="LingoPod API",
    lifespan=lifespan
)

# CORS设置
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

# API路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(configs.router, prefix="/api/v1/configs", tags=["configs"])


if __name__ == '__main__':
    logging.info("正在启动 LingoPod API 服务器...")
    uvicorn.run(
        app, 
        host=config_manager.HOST,
        port=config_manager.PORT,
        log_level="info",
        access_log=True,
        timeout_keep_alive=65
    )