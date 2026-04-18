# app/middleware/middleware_setup.py


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.custom_middleware import set_custom_headers
from app.core.logging import setup_logging
from app.api.v1.router import api_router_v1  # 正确导入
from fastapi import Request

from app.middleware.process_time import add_process_time_header

logger = setup_logging()



def register_middleware(app: FastAPI):
    logger.debug("注册中间件")

    # 注册自定义 HTTP 中间件（如增加自定义 Header）
    @app.middleware("http")
    async def set_cors_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-App-Version"] = "1.0.0"         # 用于标识服务版本
        response.headers["X-Frame-Options"] = "DENY"        # 安全防护，防止网页被嵌入 iframe（防点击劫持）
        return response

    # 注册全局 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # * 全局允许所有域，"" 禁止所有（自定义中间件可放开）
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 示例：记录所有路由
    for route in api_router_v1.routes:  # 正确：api_router，不是 router
        logger.debug(f"已注册路由: {route.path}")

    app.middleware("http")(set_custom_headers)
    app.middleware("http")(add_process_time_header)
