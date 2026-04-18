import os

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from app.api.v2.router import api_router_v2
from app.api.v1.router import api_router_v1
from app.core.config import settings
from app.core.logging import logger
from app.middleware.middleware_setup import register_middleware
from app.core.lifespan import lifespan

import sys
import uvicorn

from fastapi.responses import FileResponse



logger.debug(f"sys.modules: {list(sys.modules.keys())}")

templates = Jinja2Templates(directory=settings.template_dir)


app = FastAPI(title='settings.PROJECT_NAME', lifespan=lifespan)
# app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
# 静态文件挂载
app.mount("/static", StaticFiles(directory=settings.static_dir2), name="static")

# 注册中间件
register_middleware(app)

# 包含 API 路由
# app.include_router(api_router_v1, prefix="/api/v1")
app.include_router(api_router_v2, prefix="/api/v2")


#
# @app.get("/")
# async def root():
#     return {"message": "欢迎来到碎碎念，登录页面http://127.0.0.1:8001/static/html/login.html"}


# SPA 路由 - 所有非 API 请求返回 index.html
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """处理前端路由"""
    # 如果是 API 请求，交给对应的路由处理
    if full_path.startswith("api/"):
        return {"error": "API endpoint not found"}

    # 否则返回前端入口文件
    index_path = os.path.join(settings.webui_dir, "index.html")
    print(index_path)
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not found"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8002, reload=True)
