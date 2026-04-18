# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import demo, user, exec_sql, tweet  # 根据需要添加其他端点模块
from app.core.logging import setup_logging

logger = setup_logging()

api_router_v1 = APIRouter()
api_router_v1.include_router(demo.router, tags=["Demo"])
api_router_v1.include_router(user.router, prefix="/users", tags=["users"])
api_router_v1.include_router(exec_sql.router, prefix="/admin", tags=["users"])
api_router_v1.include_router(tweet.router, prefix="/tweet", tags=["tweet"])


# 记录包含的路由以便调试
logger.debug("API 路由器已初始化")


