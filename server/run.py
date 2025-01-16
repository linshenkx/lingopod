import uvicorn
from core.config import config_manager

if __name__ == '__main__':
    uvicorn.run(
        "main:app",
        host=config_manager.HOST,
        port=config_manager.PORT,
        reload=True,  # 开发模式下启用热重载
        log_level="info",
        access_log=True,
        timeout_keep_alive=65
    ) 