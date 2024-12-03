from datetime import datetime
import time

class TimeUtil:
    @staticmethod
    def now_ms() -> int:
        """获取当前毫秒级时间戳"""
        return int(time.time() * 1000)
    
    @staticmethod
    def to_timestamp(dt: datetime) -> int:
        """datetime 转时间戳"""
        return int(dt.timestamp() * 1000) if dt else None
    
    @staticmethod
    def from_timestamp(ts: int) -> datetime:
        """时间戳转 datetime"""
        return datetime.fromtimestamp(ts / 1000) if ts else None
    
    @staticmethod
    def from_iso(iso_str: str) -> int:
        """ISO格式字符串转时间戳"""
        return int(datetime.fromisoformat(iso_str).timestamp() * 1000)
