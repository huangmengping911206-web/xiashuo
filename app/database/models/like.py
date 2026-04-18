from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime
from app.database.models import Base

class TweetLike(Base):
    __tablename__ = "tweet_likes"
    
    id = Column(Integer, primary_key=True, index=True)
    tweet_id = Column(Integer, ForeignKey("tweets.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 联合唯一约束，防止重复点赞
    __table_args__ = (
        UniqueConstraint('tweet_id', 'user_id', name='uq_tweet_user'),
    )
