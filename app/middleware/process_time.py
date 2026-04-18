# app/middleware/process_time.py
import time
import os
from fastapi import Request
from fastapi.responses import Response
from app.core.logging import logger


IS_DEV = os.getenv("ENV", "dev") == "dev"


# ✅ 中间件函数定义（不直接注册）
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-ms"] = f"{process_time:.2f}"
    if IS_DEV:
        logger.info(f"{request.method} {request.url.path} 耗时 {process_time:.2f} ms")
    return response