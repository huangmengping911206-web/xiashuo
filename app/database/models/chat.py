from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database.models import Base


class ConversationType(enum.Enum):
    PRIVATE = "private"  # 私聊
    GROUP = "group"  # 群聊

'''
1. 会话表
这是聊天的“容器”。
核心字段：
id：主键。
type：枚举类型 (private, group)。用于区分私聊还是群聊。
name：群聊名称（私聊可为空，前端展示时动态取对方昵称）。
avatar_id：群聊头像（私聊可为空，前端取对方头像）。
owner_id：创建者（群主，私聊可为空或取发起人）。
created_at：创建时间。
'''
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), default=ConversationType.PRIVATE.value, comment="会话类型")
    name = Column(String(100), nullable=True, comment="群聊名称(私聊为空)")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="群主ID")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    members = relationship("ConversationMember", back_populates="conversation", lazy="dynamic")
    messages = relationship("Message", back_populates="conversation", lazy="dynamic")

'''
2. 会话成员表
这是“用户”与“会话”的关联表，也是实现“未读消息数”和“多端同步”的关键。
核心字段：
id：主键。
conversation_id：关联会话表。
user_id：关联用户表。
last_read_message_id：关键字段。记录该用户在这个会话中读到了哪一条。用于计算“未读消息数”。
join_time：入群时间（可用于“查找历史消息时，只看入群后的消息”）。
role：角色（如 owner, admin, member，私聊通常平等）。
'''
class ConversationMember(Base):
    __tablename__ = "conversation_members"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    join_at = Column(DateTime, default=datetime.utcnow)
    last_read_message_id = Column(Integer, default=0, comment="最后阅读消息ID，用于未读计数")

    # 关系
    conversation = relationship("Conversation", back_populates="members")
    user = relationship("User")

'''
3. 消息表
这是具体的聊天内容。
核心字段：
id：主键。
conversation_id：属于哪个会话。
sender_id：发送者。
content：消息内容（文本/JSON）。
type：消息类型（text, image, file 等）。
created_at：发送时间（用于排序）。
is_recalled：是否撤回。
'''
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(String(20))   # msg_type
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User")
