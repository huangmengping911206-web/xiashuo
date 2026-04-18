from fastapi import Request, Depends, HTTPException, status

from app.core.security import verify_access_token


async def get_user_or_401(request: Request):
    # 从 cookie 中获取 access_token
    access_token = request.cookies.get("access_token")

    # 如果没有找到 access_token，返回 401 错误
    if not access_token:
        raise HTTPException(status_code=401, detail="Access token not found in cookies")

        # 解码并验证 Token
    payload = verify_access_token(access_token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload