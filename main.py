import threading
from app import server
from app.models import init_db
from app.api import app
import uvicorn
from app.config import CONFIG  # 导入配置

if __name__ == '__main__':
    # 确保数据库和表已创建
    init_db()
    
    threading.Thread(target=server.check_and_execute_incomplete_tasks, daemon=True).start()
    
    uvicorn.run(
        app, 
        host=CONFIG['HOST'],
        port=CONFIG['PORT'],
        log_level="error",
        access_log=False,
        timeout_keep_alive=65
    )
