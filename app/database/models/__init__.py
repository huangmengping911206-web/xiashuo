# app/database/models/__init__.py

# 1. 导入两个 Base
from app.database.models.base import Base, BaseImages

# 2. 导入所有模型类 (这一步会触发模型的定义和注册)
from app.database.models.cache import CacheStore
from app.database.models.chat import Conversation, ConversationMember, Message
from app.database.models.comment import Comment
from app.database.models.message import MessageQueue
from app.database.models.user import User
from app.database.models.tweet import Tweet

from app.database.models.image import Image  # 导入图片模型
from app.database.models.stock import StockWatchlist, StockPrediction, StockBacktest  # 导入股票分析模型



# 3. 导出供其他地方使用，导出新的 Base 和模型，确保模型被注册。
__all__ = [
    "Base",
    "BaseImages",
    "User",
    "Tweet",
    "Image",
    "CacheStore",
    "MessageQueue",
    "Comment",
    "Conversation",
    "ConversationMember",
    "Message",
    "StockWatchlist",
    "StockPrediction",
    "StockBacktest",
]
