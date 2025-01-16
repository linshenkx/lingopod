from datetime import datetime, timezone
import time

class TimeUtil:
    """时间工具类"""
    
    @staticmethod
    def now() -> datetime:
        """获取当前UTC时间"""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def now_ms() -> int:
        """获取当前毫秒级时间戳"""
        return int(time.time() * 1000)
    
    @staticmethod
    def from_timestamp(timestamp: float) -> datetime:
        """从时间戳创建UTC时间"""
        return datetime.fromtimestamp(timestamp, timezone.utc)
    
    @staticmethod
    def to_timestamp(dt: datetime) -> float:
        """将datetime转换为时间戳"""
        return dt.timestamp()
    
    @staticmethod
    def from_ms(ms: int) -> datetime:
        """从毫秒级时间戳创建UTC时间"""
        return datetime.fromtimestamp(ms / 1000, timezone.utc)
    
    @staticmethod
    def to_ms(dt: datetime) -> int:
        """将datetime转换为毫秒级时间戳"""
        return int(dt.timestamp() * 1000)
