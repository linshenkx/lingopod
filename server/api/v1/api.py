from fastapi import APIRouter
from api.v1 import auth, tasks, users, configs, rss

api_router = APIRouter()

# 认证相关路由
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 任务相关路由
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])

# 用户相关路由
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 配置相关路由
api_router.include_router(configs.router, prefix="/configs", tags=["configs"])

# RSS相关路由
api_router.include_router(rss.router, prefix="/rss", tags=["rss"]) 