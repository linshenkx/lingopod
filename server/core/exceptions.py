from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from core.logging import log

async def validation_exception_handler(request: Request, exc: Exception):
    log.error(f"请求验证错误: {exc}")
    return JSONResponse(
        status_code=422,
        content={"message": "请求数据无效"},
    )

async def general_exception_handler(request: Request, exc: Exception):
    log.error(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "服务器内部错误"},
    )