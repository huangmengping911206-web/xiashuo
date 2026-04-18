from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException
from datetime import datetime
from typing import List, Tuple, Optional, Dict


class ChatService:

    @staticmethod
    async def get_or_create_private_conversation(
            db: AsyncSession, user1_id: int, user2_id: int
    ) -> Tuple[int, bool]:
        """
        获取或创建私聊会话
        返回: (会话ID, 是否新建)
        """
        # 1. 查找是否存在两人的私聊
        # 逻辑：查找既是user1所在又是user2所在的私聊会话
        # SQL技巧：使用 INTERSECT 或 JOIN 来找共同会话
        sql_find = text("""
            SELECT c.id
            FROM conversations c
            JOIN conversation_members cm1 ON c.id = cm1.conversation_id
            JOIN conversation_members cm2 ON c.id = cm2.conversation_id
            WHERE c.type = 'private'
              AND cm1.user_id = :u1
              AND cm2.user_id = :u2
            LIMIT 1
        """)
        result = await db.execute(sql_find, {"u1": user1_id, "u2": user2_id})
        row = result.fetchone()

        if row:
            return row[0], False

        # 2. 不存在，创建新的私聊会话
        now = datetime.now()

        # 插入会话表
        sql_insert_conv = text("""
            INSERT INTO conversations (type, created_at) 
            VALUES ('private', :now)
        """)
        result = await db.execute(sql_insert_conv, {"now": now})
        conv_id = result.lastrowid

        # 插入成员表 (两人)
        sql_insert_members = text("""
            INSERT INTO conversation_members (conversation_id, user_id, join_at)
            VALUES (:cid, :uid, :now)
        """)
        # 批量执行参数
        await db.execute(sql_insert_members, [
            {"cid": conv_id, "uid": user1_id, "now": now},
            {"cid": conv_id, "uid": user2_id, "now": now}
        ])

        await db.commit()
        return conv_id, True

    @staticmethod
    async def create_group_with_members(
            db: AsyncSession, creator_id: int, user_ids: List[int], name: str = None
    ) -> int:
        """创建群聊"""
        now = datetime.now()

        # 去重并确保创建者在列表中
        members = list(set(user_ids))
        if creator_id not in members:
            members.append(creator_id)

        # 获取所有成员的名字，拼接成群名
        # 构建成员 ID 列表用于 IN 查询
        member_ids_str = ",".join(str(id) for id in members)
        sql_get_names = text(f"""
            SELECT user_name FROM users WHERE id IN ({member_ids_str})
        """)
        result = await db.execute(sql_get_names)
        user_names = [row[0] for row in result.fetchall()]
        # 用成员名字拼接群名，最多显示 3 个名字
        if len(user_names) <= 3:
            group_name = "、".join(user_names)
        else:
            group_name = "、".join(user_names[:3]) + f"等{len(user_names)}人"

        # 1. 插入会话
        sql_conv = text("""
            INSERT INTO conversations (type, name, owner_id, created_at)
            VALUES ('group', :name, :owner, :now)
        """)
        result = await db.execute(sql_conv, {"name": group_name, "owner": creator_id, "now": now})
        conv_id = result.lastrowid

        # 2. 批量插入成员
        sql_members = text("""
            INSERT INTO conversation_members (conversation_id, user_id, join_at)
            VALUES (:cid, :uid, :now)
        """)
        params = [{"cid": conv_id, "uid": uid, "now": now} for uid in members]
        await db.execute(sql_members, params)

        await db.commit()
        return conv_id

    @staticmethod
    async def add_members(
            db: AsyncSession, conv_id: int, new_user_ids: List[int], operator_id: int
    ) -> Tuple[Optional[int], str]:
        """
        拉人逻辑：
        私聊 -> 创建新群
        群聊 -> 直接加人
        返回: (影响/新建的会话ID, 动作类型)
        """
        # 1. 查询当前会话类型
        sql_type = text("SELECT type FROM conversations WHERE id = :id")
        result = await db.execute(sql_type, {"id": conv_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="会话不存在")

        conv_type = row[0]

        # 2. 如果是私聊 -> 创建新群
        if conv_type == 'private':
            # 获取原私聊成员
            sql_old = text("SELECT user_id FROM conversation_members WHERE conversation_id = :cid")
            res = await db.execute(sql_old, {"cid": conv_id})
            old_members = [r[0] for r in res.fetchall()]

            # 合并新旧成员
            final_members = list(set(old_members + new_user_ids))

            # 调用创建群聊方法
            new_conv_id = await ChatService.create_group_with_members(
                db, operator_id, final_members, name="新群聊"
            )
            return new_conv_id, "private_to_group"

        # 3. 如果是群聊 -> 直接加人
        else:
            # 查询已存在的成员，防止重复
            sql_exist = text("SELECT user_id FROM conversation_members WHERE conversation_id = :cid")
            res = await db.execute(sql_exist, {"cid": conv_id})
            exist_ids = [r[0] for r in res.fetchall()]

            # 过滤出新成员
            need_add = [uid for uid in new_user_ids if uid not in exist_ids]

            if need_add:
                now = datetime.now()
                sql_add = text("""
                    INSERT INTO conversation_members (conversation_id, user_id, join_at)
                    VALUES (:cid, :uid, :now)
                """)
                params = [{"cid": conv_id, "uid": uid, "now": now} for uid in need_add]
                await db.execute(sql_add, params)
                await db.commit()

            return conv_id, "member_added"

    @staticmethod
    async def save_message(db: AsyncSession, conv_id: int, sender_id: int, content: str,
                           msg_type: str = "text"):
        """保存消息并返回完整消息体"""
        now = datetime.utcnow()

        # 1. 插入消息
        sql_insert = text("""
            INSERT INTO messages (conversation_id, sender_id, content, created_at, type)
            VALUES (:cid, :sid, :content, :now, :type)
        """)
        result = await db.execute(sql_insert, {
            "cid": conv_id, "sid": sender_id, "content": content, "now": now, "type": msg_type
        })

        msg_id = result.lastrowid

        # 2. 查询发送者信息 (用于组装返回体)
        # 实际项目中建议缓存用户信息，减少 DB 查询
        sql_user = text("SELECT user_name, avatar_id FROM users WHERE id = :uid")
        user_res = await db.execute(sql_user, {"uid": sender_id})
        user = user_res.fetchone()

        await db.commit()

        # 3. 组装返回给前端的数据结构
        # 注意：avatar_id 可能需要拼接成完整 URL，这里假设前端处理或后端拼接
        return {
            "id": msg_id,
            "conversation_id": conv_id,
            "sender_id": sender_id,
            "sender_name": user.user_name if user else "Unknown",
            "sender_avatar_id": user.avatar_id if user else None,
            "content": content,
            "type": msg_type,
            "created_at": now.isoformat()
        }

    @staticmethod
    async def search_users(db: AsyncSession, keyword: str, current_user_id: int, limit: int = 20) -> List[Dict]:
        """搜索用户（排除自己）"""
        sql = text("""
                SELECT id, user_name, avatar_id 
                FROM users 
                WHERE (user_name LIKE :kw OR email LIKE :kw) 
                  AND id != :uid
                LIMIT :limit
            """)
        # 模糊搜索
        params = {"kw": f"%{keyword}%", "uid": current_user_id, "limit": limit}
        result = await db.execute(sql, params)

        # 转换为字典列表
        users = []
        for row in result.mappings().all():
            users.append(dict(row))
        return users

    @staticmethod
    async def get_conversation_messages(
            db: AsyncSession, conv_id: int, before_id: int = 0, limit: int = 20
    ) -> List[Dict]:
        """
        拉取历史记录
        :param before_id: 上一页最后一条消息的ID，用于向下翻页
        """
        if before_id == 0:
            # 第一页，取最新的
            sql = text("""
                    SELECT m.id, m.conversation_id, m.sender_id, m.content, m.created_at,
                           u.user_name as sender_name, u.avatar_id as sender_avatar_id, m.type
                    FROM messages m
                    JOIN users u ON m.sender_id = u.id
                    WHERE m.conversation_id = :cid
                    ORDER BY m.id DESC
                    LIMIT :limit
                """)
            params = {"cid": conv_id, "limit": limit}
        else:
            # 翻页，取 ID 小于 before_id 的
            sql = text("""
                    SELECT m.id, m.conversation_id, m.sender_id, m.content, m.created_at,
                           u.user_name as sender_name, u.avatar_id as sender_avatar_id
                    FROM messages m
                    JOIN users u ON m.sender_id = u.id
                    WHERE m.conversation_id = :cid AND m.id < :bid
                    ORDER BY m.id DESC
                    LIMIT :limit
                """)
            params = {"cid": conv_id, "bid": before_id, "limit": limit}

        result = await db.execute(sql, params)
        # 返回列表，注意顺序通常是倒序或者前端处理
        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    async def get_conversation_list(db: AsyncSession, user_id: int) -> List[Dict]:
        """获取用户的会话列表（含未读数、最后一条消息）"""
        # 这是一个比较复杂的聚合查询
        # 1. 找到所有会话
        # 2. 关联最后一条消息
        # 3. 计算未读数 (message.id > member.last_read_message_id)
        # 4. 处理私聊的名称/头像（取对方的）

        # 简化版 SQL 示例：
        sql = text("""
                SELECT 
                    c.id, c.type, c.name as group_name,
                    cm.last_read_message_id,
                    (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id AND m.id > cm.last_read_message_id) as unread_count,
                    (SELECT content FROM messages m WHERE m.conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_message,
                    (SELECT created_at FROM messages m WHERE m.conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_message_time
                FROM conversation_members cm
                JOIN conversations c ON cm.conversation_id = c.id
                WHERE cm.user_id = :uid
                ORDER BY last_message_time DESC
            """)
        sql_with_members_id = text("""
                        SELECT 
                            c.id, c.type, c.name as group_name,
                            cm.last_read_message_id,
                            (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id AND m.id > cm.last_read_message_id) as unread_count,
                            (SELECT content FROM messages m WHERE m.conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_message,
                            (SELECT created_at FROM messages m WHERE m.conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_message_time,
                            -- 【修改】聚合其他成员ID，用逗号分隔
                            (
                                SELECT group_concat(cm2.user_id, ',')
                                FROM conversation_members cm2
                                WHERE cm2.conversation_id = c.id 
                                AND cm2.user_id != :uid  -- 排除当前用户
                            ) as member_ids_str
                        FROM conversation_members cm
                        JOIN conversations c ON cm.conversation_id = c.id
                        WHERE cm.user_id = :uid
                        ORDER BY last_message_time DESC
                    """)
        # 将之前返回 member_ids_str 的子查询改为返回 JSON 对象列表
        sql_with_members_avatar_id = text("""
            SELECT 
                c.id, 
                c.type, 
                c.name as group_name,
                cm.last_read_message_id,
                (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id AND m.id > cm.last_read_message_id) as unread_count,
                (SELECT content FROM messages m WHERE m.conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_message,
                (SELECT created_at FROM messages m WHERE m.conversation_id = c.id ORDER BY id DESC LIMIT 1) as last_message_time,

                -- 【修改】返回包含 id 和 avatar_id 的 JSON 数组字符串
                (
                    SELECT json_group_array(json_object(
                        'id', u.id,
                        'username', u.user_name,
                        'avatar_id', u.avatar_id
                    ))
                    FROM conversation_members cm2
                    JOIN users u ON cm2.user_id = u.id
                    WHERE cm2.conversation_id = c.id 
                    AND cm2.user_id != :uid
                ) as other_members_json

            FROM conversation_members cm
            JOIN conversations c ON cm.conversation_id = c.id
            WHERE cm.user_id = :uid
            ORDER BY last_message_time DESC
        """)

        result = await db.execute(sql_with_members_avatar_id, {"uid": user_id})

        # 这里的数据处理逻辑：
        # 如果是群聊，name 直接用 group_name
        # 如果是私聊，name 需要查对方的 user_name (这里暂时省略二次查询，实际建议在SQL中join users表处理)

        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    async def recall_message(db: AsyncSession, message_id: int, user_id: int):
        """撤回消息"""
        # 1. 查消息
        msg = await db.execute(text("SELECT * FROM messages WHERE id = :id"), {"id": message_id})
        msg = msg.fetchone()
        if not msg or msg['sender_id'] != user_id:
            return False  # 无权撤回或不存在

        # 2. 删除或标记 (物理删除或逻辑删除)
        await db.execute(text("DELETE FROM messages WHERE id = :id"), {"id": message_id})
        await db.commit()
        return True

    @staticmethod
    async def get_member_ids(db: AsyncSession, conv_id: int) -> list[int]:
        """
        获取会话内所有成员的ID列表
        用于 WebSocket 推送时确定接收者
        """
        sql = text("""
                SELECT user_id 
                FROM conversation_members 
                WHERE conversation_id = :cid
            """)
        result = await db.execute(sql, {"cid": conv_id})

        # result.fetchall() 返回的是 Row 对象列表，如 [(1,), (2,)]
        # 我们用列表推导式把它们解包成 [1, 2]
        return [row[0] for row in result.fetchall()]
    @staticmethod
    async def update_group_name(db: AsyncSession, conv_id: int, name: str, user_id: int) -> bool:
        """
        修改群聊名称（仅群主可修改）
        """
        # 1. 查询会话信息和所有者
        sql = text("""
            SELECT type, owner_id FROM conversations WHERE id = :id
        """)
        result = await db.execute(sql, {"id": conv_id})
        row = result.fetchone()
        
        if not row:
            return False
        
        conv_type, owner_id = row
        
        # 2. 仅群聊可以修改名称，且必须是群主
        if conv_type != 'group' or owner_id != user_id:
            return False
        
        # 3. 更新名称
        update_sql = text("""
            UPDATE conversations SET name = :name WHERE id = :id
        """)
        from datetime import datetime
        await db.execute(update_sql, {"name": name, "now": datetime.now(), "id": conv_id})
        await db.commit()
        return True
