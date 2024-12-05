from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from core.logging import log
from pydantic import ValidationError

async def validation_exception_handler(request: Request, exc: Exception):
    # 获取错误详情
    errors = exc.errors()
    error_msg = errors[0].get('msg', '') if errors else ''
    
    # 记录详细的错误信息
    log.error(f"验证失败: {exc}")
    
    # 直接返回原始错误消息
    return JSONResponse(
        status_code=422,
        content={"message": error_msg}
    )
    

async def general_exception_handler(request: Request, exc: Exception):
    log.error(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "服务器内部错误"},
    )