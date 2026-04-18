"""
AI 助手服务 - 调用智谱 AI 大模型
"""
import json
import urllib.request
import urllib.error
import os
from pathlib import Path
from app.core.logging import logger
from app.services.ai_personas import get_system_prompt

# 从.env 读取 token
ENV_FILE = Path(__file__).parent.parent / ".env"
AI_TOKEN = ""
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith("ZHIPU_TOKEN="):
                AI_TOKEN = line.strip().split("=", 1)[1]
                break

# 如果.env 没有，使用默认值
if not AI_TOKEN:
    AI_TOKEN = "561aa875c9584c0ca9196da1a3b26964.BOgVVjwbGmgcAY1u"

API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

async def get_ai_reply(user_message: str, target_user_id: int, conversation_history: list = None) -> str:
    """
    调用智谱 AI 获取回复
    
    Args:
        user_message: 用户消息
        target_user_id: 目标 AI 用户 ID（用于加载对应人设）
        conversation_history: 对话历史（可选）
    
    Returns:
        AI 回复内容
    """
    messages = [
        {"role": "system", "content": get_system_prompt(target_user_id)},
        {"role": "user", "content": user_message}
    ]
    
    # 如果有对话历史，添加到 messages
    if conversation_history:
        for msg in conversation_history[-5:]:  # 只保留最近 5 条
            messages.insert(1, msg)
    
    data = json.dumps({
        "model": "glm-4-flash",
        "messages": messages,
        "stream": False,
        "temperature": 0.7,
        "thinking": {
            "type": "enabled"
        }
    }).encode('utf-8')
    
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {AI_TOKEN}'
        },
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            reply = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            logger.info(f"[AI] 回复：{reply[:100]}...")
            return reply
    except Exception as e:
        logger.error(f"[AI] 调用失败：{e}")
        return "抱歉，我暂时无法回复，请稍后再试。"
