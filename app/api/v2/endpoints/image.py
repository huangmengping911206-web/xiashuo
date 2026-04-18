# app/api/endpoints/images.py
import base64

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_image_session
from app.services.image_service import ImageService
from app.database.schemas.image import ImageDetailOut, ImageOut

router = APIRouter()


# 1. 上传接口
# response_model=ImageOut 确保即使 model 里有 data，返回给前端时也会被过滤掉
@router.post("/upload", response_model=ImageOut)
async def upload_image(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_image_session)
):
    user_id = 1  # 模拟当前登录用户
    return await ImageService.upload_image(db, file, user_id)


# 2. 查询个人名下所有图片 (不含 Base64)
# 【注意】这个路由必须放在 /{image_id} 前面，否则 "user" 会被当成 image_id
@router.get("/user/{user_id}", response_model=list[ImageOut])
async def get_user_images(
        user_id: int,
        db: AsyncSession = Depends(get_image_session)
):
    return await ImageService.get_images_by_user(db, user_id)


# 3. 查询图片详情：直接返回图片二进制流
# 前端使用：<img src="http://host/images/1" />
@router.get("/{image_id}")
async def get_image_stream(
        image_id: int,
        db: AsyncSession = Depends(get_image_session)
):
    # 获取数据库记录
    image = await ImageService.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片未找到")

    # 【核心逻辑】将 Base64 字符串解码为二进制数据
    try:
        image_bytes = base64.b64decode(image.image_data)
    except Exception:
        raise HTTPException(status_code=500, detail="图片数据解码失败")

    # 【浏览器缓存支持】
    # 生成 ETag (实体标签)，用于标识资源版本
    # 这里简单使用 id + 文件大小作为唯一标识
    etag = f'W/"{image.id}-{image.file_size}"'

    # 【核心修复】构建响应并设置缓存头
    headers = {
        "Cache-Control": "public, max-age=864000",  # public: 允许中间代理缓存, max-age: 缓存10天
        "ETag": etag,
        # "Content-Type" 会由 media_type 参数自动设置，不需要手动加到 headers 字典
    }

    return Response(
        content=image_bytes,
        media_type=image.file_type,
        headers=headers
    )



# 4. 删除接口
@router.delete("/{image_id}")
async def delete_image(
        image_id: int,
        db: AsyncSession = Depends(get_image_session)
):
    return await ImageService.delete_image(db, image_id)

