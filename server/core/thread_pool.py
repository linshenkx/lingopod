from concurrent.futures import ThreadPoolExecutor, Future
import threading
from typing import Callable, Any
from core.logging import log
from core.config import settings

class ThreadPoolManager:
    """线程池管理器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            # 从配置文件读取最大并发数，默认为3
            self.max_workers = getattr(settings, 'MAX_TASK_WORKERS', 3)
            self.executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix='task_worker'
            )
            self.initialized = True
            log.info(f"线程池初始化完成，最大并发数: {self.max_workers}")
    
    @classmethod
    def get_instance(cls) -> 'ThreadPoolManager':
        """获取线程池管理器实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        """提交任务到线程池
        
        Args:
            fn: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Future: 用于跟踪任务执行状态的Future对象
        """
        return self.executor.submit(fn, *args, **kwargs)
    
    def set_max_workers(self, max_workers: int):
        """设置最大工作线程数
        
        Args:
            max_workers: 最大工作线程数
        """
        if max_workers != self.max_workers:
            log.info(f"更新线程池最大并发数: {self.max_workers} -> {max_workers}")
            # 关闭当前线程池
            self.shutdown()
            # 创建新的线程池
            self.max_workers = max_workers
            self.executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix='task_worker'
            )
    
    def shutdown(self, wait: bool = True):
        """关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=wait)
            log.info("线程池已关闭") 