# app/database/schemas/image.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


# 1. 基础元数据模型 (不含 Base64 数据)
class ImageOut(BaseModel):
    id: int
    uploader_id: int
    filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 2. 详情模型 (包含 Base64 数据)
class ImageDetailOut(ImageOut):
    image_data: str  # 仅在详情中返回此字段

    # 辅助字段：方便前端直接使用
    @property
    def data_url(self) -> str:
        """返回完整的 Data URL 格式"""
        return f"data:{self.file_type};base64,{self.image_data}"