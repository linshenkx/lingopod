from functools import wraps
from core.logging import log

def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.error(f"函数 {func.__name__} 执行出错: {str(e)}")
            raise
    return wrapper
