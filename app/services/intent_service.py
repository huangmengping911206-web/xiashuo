"""
意图识别服务
判断用户消息是否是发布推文指令
"""
import json
import urllib.request
import os
from pathlib import Path

# 从.env 读取 token
ENV_FILE = Path(__file__).parent.parent / ".env"
AI_TOKEN = ""
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith("ZHIPU_TOKEN="):
                AI_TOKEN = line.strip().split("=", 1)[1]
                break

if not AI_TOKEN:
    AI_TOKEN = "561aa875c9584c0ca9196da1a3b26964.BOgVVjwbGmgcAY1u"

API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

INTENT_PROMPT = """请判断用户是否想发布推文。

如果是发布推文，返回 JSON：
{"intent": "publish_tweet", "content": "推文内容"}

如果只是普通聊天，返回 JSON：
{"intent": "chat"}

推文发布指令示例：
- "帮我发一条推文，内容是..."
- "发布推文：..."
- "发一条：..."
- "tweet: ..."
- "post: ..."
- "我想发推文..."
- "发布一条..."

注意：
- 只返回 JSON，不要其他内容
- 推文内容要提取完整
"""

async def detect_intent(message: str) -> dict:
    """
    检测用户意图
    
    Args:
        message: 用户消息
    
    Returns:
        {"intent": "publish_tweet"|"chat", "content": "推文内容 (如果有)"}
    """
    messages = [
        {"role": "system", "content": INTENT_PROMPT},
        {"role": "user", "content": message}
    ]
    
    data = json.dumps({
        "model": "glm-5",
        "messages": messages,
        "stream": False,
        "temperature": 0.1  # 低温度，确保判断准确
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
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            reply = result.get('choices', [{}])[0].get('message', {}).get('content', '{}')
            
            # 解析 JSON
            try:
                intent_data = json.loads(reply.strip())
                return intent_data
            except:
                # 解析失败，默认是聊天
                return {"intent": "chat"}
                
    except Exception as e:
        from app.core.logging import logger
        logger.error(f"[意图识别] 失败：{e}")
        return {"intent": "chat"}
