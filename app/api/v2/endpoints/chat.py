from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
import time
from app.core.socket_manager import manager
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.check_user import get_user_or_401
from app.core.security import verify_access_token
from app.database.session import get_session
from app.services.chat_service import ChatService
from app.database.models.user import User
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query

from app.services.message_service import QueueService

router = APIRouter()


class SendMessageSchema(BaseModel):
    conversation_id: int
    content: str


@router.post("/conversations/private/{target_user_id}", summary="创建私聊")
async def create_private_chat(
        target_user_id: int,
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401)
):
    """创建/获取私聊"""
    conv_id, created = await ChatService.get_or_create_private_conversation(
        db, user['user_id'], target_user_id
    )
    return {"id": conv_id, "type": 'private'}


@router.post("/conversations/group", summary="创建群聊")
async def create_group(
        user_ids: list[int],
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401)
):
    """创建群聊"""
    conv_id = await ChatService.create_group_with_members(db, user['user_id'], user_ids)
    return {"id": conv_id, "type": "group"}


@router.post("/conversations/{conv_id}/members", summary="群聊拉人")
async def add_members(
        conv_id: int,
        user_ids: list[int],
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401)
):
    """
    拉人接口：
    如果是私聊，会返回新群的ID
    """
    conv_id, action_type = await ChatService.add_members(db, conv_id, user_ids, user['user_id'])

    # 如果是私聊转群聊，需要通知前端切换窗口
    if action_type == "private_to_group":
        # 通知相关用户
        return {"msg": "已创建新群聊", "new_conversation_id": conv_id, "action": "redirect"}

    return {"msg": "成员添加成功", "conversation_id": conv_id}


@router.get("/users/search")
async def search_users(
        keyword: str = Query(..., min_length=1),
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401)
):
    users = await ChatService.search_users(db, keyword, user['user_id'])
    return {"data": users}


@router.get("/conversations")
async def get_conversations(
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401)
):
    list_data = await ChatService.get_conversation_list(db, user['user_id'])
    return {"data": list_data}


@router.get("/conversations/{id}/messages")
async def get_history(
        id: int,
        before_id: int = Query(0, description="上一页最后一条消息ID，首次加载传0"),
        limit: int = 20,
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401)
):
    # 权限校验：确保用户在该会话中
    # ... 省略校验代码 ...

    messages = await ChatService.get_conversation_messages(db, id, before_id, limit)
    return messages


# 群聊 AI 回复缓存：{conv_id: {"last_ai_id": user_id, "last_reply_time": timestamp}}
# 用于防止 AI 连续回复，只有人类发言后 AI 才能再次回复
CONV_AI_CACHE = {}

# GLM 自动发布推文配置
GLM_USER_ID = 8  # GLM47Flush 的 user_id

# --- WebSocket 路由 ---
@router.websocket("/ws")
async def websocket_endpoint(
        websocket: WebSocket,
        db: AsyncSession = Depends(get_session)
):
    cookies = websocket.cookies
    print("收到的 Cookies:", cookies)
    print("收到的 token:", cookies.get('access_token', None))

    if cookies:
        payload = verify_access_token(cookies.get('access_token', None))
        print("用户信息:", payload)
    else:
        print('websocket 无 cookie')
        return 'websocket 无 cookie'
    # 这里假设已解析出 user_id
    user_id = payload.get('user_id')

    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            print('请求', data)

            ''''
            前端发送格式：
            {
                    "event":"send_message",
                    "data":{"conversation_id":4,
                    "content":"76",
                    "type":"image"}
            }
            

            new_message	新消息	Message Object (含id, content, sender_id…)	有人发消息
            notification	系统通知	{ "type": "kicked", "msg": "..." }	被踢出、系统公告
            chat_upgraded	私聊升群	{ "old_id": 1, "new_id": 2 }	关键：私聊拉人后，通知前端跳转
            user_typing	输入状态	{ "conversation_id": 1, "user_id": 2, "is_typing": true }	对方正在输入
            message_recalled	消息撤回	{ "message_id": 55 }	有人撤回消息
            '''
            event = data.get("event")
            payload = data.get("data", {})
            conv_id = payload.get('conversation_id')
            content = payload.get('content')
            msg_type = payload.get('type', None) or 'text'

            # 处理发送消息逻辑
            if event == "send_message":
                # 1. 保存并获取完整消息体
                msg_data = await ChatService.save_message(db, conv_id, user_id, content, msg_type)
                
                # 2. 获取会话成员 ID
                member_ids = await ChatService.get_member_ids(db, conv_id)
                
                # 3. 直接推送用户消息（立刻显示，不经过队列）
                push_msg = {
                    "event": "send_message",
                    "msg_data": msg_data,
                    "member_ids": member_ids
                }
                await manager.broadcast_to_conversation(conv_id, push_msg, member_ids)
                
                # 2. 获取会话成员
                member_ids = await ChatService.get_member_ids(db, conv_id)
                
                # 3. 检测是否发送给 AI 助手，并检查是否需要回复
                from app.services.ai_models import get_all_ai_models
                ai_models = await get_all_ai_models()
                ai_user_ids = set(ai_models.values())
                
                # 检查会话中是否有 AI 用户，且不是 AI 自己发的
                if ai_user_ids & set(member_ids) and user_id not in ai_user_ids:
                    # 找到第一个 AI 用户的 ID
                    ai_user_id = list(ai_user_ids & set(member_ids))[0]
                    
                    # 特殊处理：如果是发给 GLM 的消息，先判断意图
                    if ai_user_id == GLM_USER_ID:
                        # 异步处理 GLM 消息（意图识别 + 回复/发布）
                        import asyncio
                        asyncio.create_task(_handle_glm_message(db, conv_id, content, member_ids, user_id))
                    else:
                        # 其他 AI，直接回复
                        import asyncio
                        asyncio.create_task(_handle_ai_reply(db, conv_id, content, member_ids, ai_user_id))

                # 5. 推送（已提前推送，这里跳过）
                continue
                # 注意：发送者自己也需要收到这条消息（为了同步多端、更新本地界面）
                # 所以前端逻辑通常是：发送时先显示loading，收到WS回包后替换loading为正式消息
                # 消息示例

                data = {
                    "event": "send_message",
                    "msg_data": msg_data,
                    "member_ids": member_ids
                }
                queue_message = {
                    "event": "send_message",
                    "data": data
                }
                print('f发送消息', queue_message)
                await QueueService.publish(
                    db=db,
                    topic="email",
                    payload={"user": "user_in.user_name", "type": "welcome"}
                )
                await QueueService.publish(db=db, topic="chat", payload=queue_message)


            elif event == "typing":
                # 正在输入状态

                # 查询会话成员
                member_ids = [...]  # 查询逻辑

                # 构造数据：告诉其他人 "我正在输入"
                typing_data = {
                    "conversation_id": conv_id,
                    "user_id": user_id,
                    "is_typing": True
                }
                # 排除自己，推送给其他人
                for uid in member_ids:
                    if uid != user_id:
                        await manager.send_personal_message(
                            {"event": "user_typing", "data": typing_data},
                            uid
                        )

            elif event == "recall":
                msg_id = payload['message_id']
                success = await ChatService.recall_message(db, msg_id, user_id)
                if success:
                    # 广播撤回通知
                    # 需查出该消息属于哪个会话
                    # 推送: {"event": "message_recalled", "data": {"id": msg_id}}
                    pass

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@router.put("/conversations/{conv_id}/name", summary="修改群聊名称")
async def update_group_name(
        conv_id: int,
        name: str,
        db: AsyncSession = Depends(get_session),
        user=Depends(get_user_or_401)
):
    """
    修改群聊名称（仅群主或管理员可修改）
    """
    success = await ChatService.update_group_name(db, conv_id, name, user['user_id'])
    if success:
        return {"msg": "修改成功", "conversation_id": conv_id, "name": name}
    else:
        raise HTTPException(status_code=403, detail="无权限修改群聊名称")


async def _handle_ai_reply(db, conv_id: int, user_message: str, member_ids: list, ai_user_id: int = 8):
    """异步处理 AI 回复（不阻塞用户消息显示）"""
    try:
        from app.services.ai_service import get_ai_reply
        from app.services.chat_service import ChatService
        from app.core.socket_manager import manager
        
        # 调用 AI，传入 AI 用户 ID 以加载对应人设
        ai_reply = await get_ai_reply(user_message, ai_user_id)
        if ai_reply:
            # 保存 AI 回复
            ai_msg = await ChatService.save_message(db, conv_id, ai_user_id, ai_reply, "text")
            # 直接推送 AI 回复
            push_msg = {
                "event": "send_message",
                "msg_data": ai_msg,
                "member_ids": member_ids
            }
            await manager.broadcast_to_conversation(conv_id, push_msg, member_ids)
    except Exception as e:
        from app.core.logging import logger
        logger.error(f"[AI 回复] 失败：{e}")

async def _handle_glm_message(db, conv_id: int, user_message: str, member_ids: list, sender_user_id: int):
    """
    处理 GLM 收到的消息：
    1. 判断意图（发布推文 or 聊天）
    2. 发布推文：直接插入数据库
    3. 聊天：正常回复
    """
    try:
        from app.services.intent_service import detect_intent
        from app.services.ai_service import get_ai_reply
        from app.services.chat_service import ChatService
        from app.core.socket_manager import manager
        from sqlalchemy import text
        from datetime import datetime
        
        # 1. 意图识别
        intent = await detect_intent(user_message)
        
        if intent.get('intent') == 'publish_tweet':
            # 2. 发布推文（直接插入数据库）
            tweet_content = intent.get('content', user_message)
            
            try:
                # 直接插入推文
                now = datetime.now()
                sql_insert = text("""
                    INSERT INTO tweets (creater_id, tweet, tags, is_published, status, created_at, updated_at)
                    VALUES (:creater_id, :tweet, :tags, :is_published, :status, :now, :now)
                """)
                
                await db.execute(sql_insert, {
                    "creater_id": sender_user_id,
                    "tweet": tweet_content,
                    "tags": "AI,自动发布",
                    "is_published": True,
                    "status": True,
                    "now": now
                })
                
                # 获取刚插入的推文 ID
                sql_last = text("SELECT last_insert_rowid()")
                result = await db.execute(sql_last)
                tweet_id = result.fetchone()[0]
                
                await db.commit()
                
                # 发布成功，回复用户
                reply = f"✅ 已帮你发布推文！ID: {tweet_id}\n\n内容：{tweet_content[:50]}..."
                
                # 保存 GLM 回复
                ai_msg = await ChatService.save_message(db, conv_id, GLM_USER_ID, reply, "text")
                
                # 推送回复
                push_msg = {
                    "event": "send_message",
                    "msg_data": ai_msg,
                    "member_ids": member_ids
                }
                await manager.broadcast_to_conversation(conv_id, push_msg, member_ids)
                
            except Exception as e:
                from app.core.logging import logger
                logger.error(f"[GLM 发布推文] 失败：{e}")
                # 发布失败，回复用户
                reply = f"❌ 发布失败：{str(e)}"
                ai_msg = await ChatService.save_message(db, conv_id, GLM_USER_ID, reply, "text")
                push_msg = {
                    "event": "send_message",
                    "msg_data": ai_msg,
                    "member_ids": member_ids
                }
                await manager.broadcast_to_conversation(conv_id, push_msg, member_ids)
        else:
            # 3. 普通聊天，正常回复
            ai_reply = await get_ai_reply(user_message, GLM_USER_ID)
            if ai_reply:
                ai_msg = await ChatService.save_message(db, conv_id, GLM_USER_ID, ai_reply, "text")
                push_msg = {
                    "event": "send_message",
                    "msg_data": ai_msg,
                    "member_ids": member_ids
                }
                await manager.broadcast_to_conversation(conv_id, push_msg, member_ids)
                
    except Exception as e:
        from app.core.logging import logger
        logger.error(f"[GLM 消息处理] 失败：{e}")