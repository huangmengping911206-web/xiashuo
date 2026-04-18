from fastapi.responses import JSONResponse
from functools import wraps


# ============================================================
# ✅ 自定义装饰器：为特定接口设置 CORS 头（更细粒度控制）
# ============================================================
def custom_cors(
    origins: list,
    methods: list = ["GET"],
    headers: list = ["Content-Type"],
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 执行原函数
            response = await func(*args, **kwargs)

            # 自动将 dict 转为 JSONResponse
            if isinstance(response, dict):
                response = JSONResponse(content=response)

            # 设置自定义 CORS 响应头
            response.headers["Access-Control-Allow-Origin"] = ", ".join(origins)
            response.headers["Access-Control-Allow-Methods"] = ", ".join(methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(headers)

            return response
        return wrapper
    return decorator


'''
@app.get("/special")
@custom_cors(["https://example.com"], methods=["GET", "POST"])
async def special_endpoint():
    return {"message": "This endpoint allows example.com only."}
'''