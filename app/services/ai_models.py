"""
AI 模型配置服务
支持动态配置 AI 助手，不硬编码 user_id
"""

# AI 模型配置（从数据库或配置加载）
# 格式：{模型名称：user_id}
AI_MODELS = {
    "GLM47Flush": 8,
    "GLM-4-Flash": 8,
    "GLM4": 8,
    "groook": 4,
    "deepthink": 3,
}

async def get_all_ai_models() -> dict:
    """获取所有 AI 模型配置"""
    return AI_MODELS.copy()

async def get_ai_model_user_id(model_name: str) -> int:
    """根据模型名称获取对应的 user_id"""
    return AI_MODELS.get(model_name)

async def is_ai_user(user_id: int) -> bool:
    """判断是否是 AI 用户"""
    return user_id in AI_MODELS.values()

async def get_ai_model_name(user_id: int) -> str:
    """根据 user_id 获取模型名称"""
    for name, uid in AI_MODELS.items():
        if uid == user_id:
            return name
    return None
