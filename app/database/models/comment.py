# app/database/models/comment.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from datetime import datetime
from app.database.models import Base


class Comment(Base):
    __tablename__ = "comments"  # 建议复数形式

    id = Column(Integer, primary_key=True, index=True)

    # === 核心修正 ===
    # 1. 关联推文：这条评论属于哪条推文？
    tweet_id = Column(Integer, ForeignKey("tweets.id"), index=True, nullable=False)

    # 2. 关联用户：谁发的？
    creater_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    content = Column(Text, nullable=False)  # 评论内容，建议用 Text
    tags = Column(String(255))  # 标签

    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # 经常按时间排序，加索引

    # relationship 修正：backref 应该叫 "comments"，因为 User 拥有的是 "comments" 列表
    # creater = relationship("User", backref="comments")
