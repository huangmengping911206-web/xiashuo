# app/services/image_service.py
import base64
import io
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from PIL import Image as PILImage  # 引入 Pillow
from app.database.models.image import Image


class ImageService:

    @staticmethod
    def _compress_image(image_bytes: bytes, quality: int = 75, max_width: int = 800) -> tuple[bytes, str]:
        """
        内部方法：压缩图片
        :param image_bytes: 原始图片二进制数据
        :param quality: 压缩质量 (1-100)
        :param max_width: 最大宽度，超过则等比缩放
        :return: (压缩后的二进制数据, 格式类型)
        """
        try:
            # 1. 打开图片
            img = PILImage.open(io.BytesIO(image_bytes))

            # 2. 处理旋转信息 (有些手机拍照有 EXIF 旋转信息)
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except:
                pass  # 如果没有 EXIF 信息则忽略

            # 3. 调整尺寸 (保持宽高比)
            if img.width > max_width:
                ratio = max_width / float(img.width)
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), PILImage.Resampling.LANCZOS)

            # 4. 格式转换与压缩
            # 统一转为 JPEG 格式以获得更好的压缩率 (如果不支持透明通道)
            # 如果原格式是 PNG 且需要透明通道，可以保留 PNG，但这里为了演示压缩效果统一转 JPEG
            output_format = "JPEG"

            # 处理 RGBA (透明通道) -> RGB (JPEG 不支持透明)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 5. 保存到内存流
            buffer = io.BytesIO()
            img.save(buffer, format=output_format, quality=quality, optimize=True)
            compressed_bytes = buffer.getvalue()

            return compressed_bytes, f"image/{output_format.lower()}"

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"图片处理失败: {str(e)}")

    @staticmethod
    async def upload_image(db: AsyncSession, file: UploadFile, uploader_id: int):
        # 1. 校验类型
        if file.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(status_code=400, detail="仅支持图片格式")

        # 2. 读取二进制数据
        contents = await file.read()

        # 3. 【核心】压缩图片
        # 这里设置质量为 75，最大宽度 800px
        compressed_bytes, file_type = ImageService._compress_image(
            contents, quality=75, max_width=800
        )

        # 4. 转 Base64
        base64_str = base64.b64encode(compressed_bytes).decode('utf-8')

        # 5. 存入数据库
        new_image = Image(
            uploader_id=uploader_id,
            filename=file.filename,
            image_data=base64_str,
            file_type=file_type,
            file_size=len(compressed_bytes)  # 记录压缩后的大小
        )

        db.add(new_image)
        await db.commit()
        await db.refresh(new_image)

        return new_image

    @staticmethod
    async def delete_image(db: AsyncSession, image_id: int):
        image = await ImageService.get_image(db, image_id)
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")

        await db.delete(image)
        await db.commit()
        return {"message": "删除成功"}

    @staticmethod
    async def get_image(db: AsyncSession, image_id: int):
        """获取单张图片（含数据）"""
        result = await db.execute(select(Image).where(Image.id == image_id))
        return result.scalars().first()

    @staticmethod
    async def get_images_by_user(db: AsyncSession, user_id: int):
        """
        查询个人名下所有图片（不含数据）
        使用 load_only 或者在 select 中指定列，防止加载巨大的 Text 字段
        """
        # 方式一：直接查询对象，但在 SQL 层面排除大字段
        stmt = select(Image).where(Image.uploader_id == user_id)

        result = await db.execute(stmt)
        return result.scalars().all()