# app/api/v2/router.py
from fastapi import APIRouter, Depends
from app.api.v2.endpoints import user, tweet, image, monitoring, comment, chat  # 根据需要添加其他端点模块
from app.core.check_user import get_user_or_401
from app.core.logging import setup_logging
from fastapi.security import APIKeyCookie


logger = setup_logging()

api_router_v2 = APIRouter()

api_router_v2.include_router(user.router, prefix="/users", tags=["users"])
api_router_v2.include_router(tweet.router, prefix="/tweet", tags=["tweet"],
                             dependencies=[Depends(get_user_or_401)])
api_router_v2.include_router(image.router, prefix="/image", tags=["image"])
api_router_v2.include_router(comment.router, prefix="/comment", tags=["评论"],
                             dependencies=[Depends(get_user_or_401)])
api_router_v2.include_router(chat.router, prefix="/chat", tags=["聊天"]
                             )
api_router_v2.include_router(monitoring.router, prefix="/monitoring", tags=["监控"],
                             dependencies=[Depends(get_user_or_401)])



# 记录包含的路由以便调试
logger.debug("API 路由器已初始化 v2")


