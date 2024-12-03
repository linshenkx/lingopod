from loguru import logger
import sys
from pathlib import Path
from core.config import settings

# 创建日志目录
log_path = Path(settings.BASE_DIR) / "logs"
log_path.mkdir(exist_ok=True)

# 移除默认的处理器
logger.remove()

# 添加控制台处理器
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
    level="INFO",
    colorize=True
)

# 添加文件处理器
logger.add(
    log_path / "app.log",
    rotation="500 MB",
    retention="10 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    level="INFO",
    encoding="utf-8"
)

# 导出 logger 实例
log = logger