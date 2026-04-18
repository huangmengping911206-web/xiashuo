# app/database/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from sqlalchemy import text

# 【关键】导入两个 Base,【关键】必须显式导入你的其他模型，即使代码里没直接用到！
from app.database.models import Base, BaseImages

# 1. 主数据库引擎 (用户、推文等)
engine = create_async_engine(settings.DATABASE_URL, echo=False)
# 2. 图片数据库引擎
engine_images = create_async_engine(settings.IMAGES_DATABASE_URL, echo=False)


# 异步会话工厂
# 主数据库会话
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
# 图片数据库会话
image_async_session_factory = async_sessionmaker(engine_images, class_=AsyncSession, expire_on_commit=False)


# 初始化数据库表
async def init_db():
    # 创建主数据库表 (User, Tweet 等)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # 2. 创建 FTS 虚拟表
        # 【修正】列名改为 'tweet'，与模型字段一致
        # 正确的建表语句 (配合 Jieba 方案)为了让上述 UPDATE 语句正常工作，
        # 你的 init_db 中创建虚拟表的语句必须是独立模式（不带 content='tweets'）
        # 如果之前带了 content='tweets'，请删除数据库文件重新生成，或者重建表，
        # 否则直接 UPDATE 可能会报错或数据不同步。
        await conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS tweets_fts USING fts5(
                tweet,
                tokenize='unicode61'
            );
        """))

        # 开启WAL模式：这是性能的基石，解决“读写互斥”问题，大幅提升并发性能。
        # 1. 开启 WAL 模式 (解决高并发读写锁问题)
        await conn.execute(text("PRAGMA journal_mode=WAL;"))

        # 2. 设置同步模式为 NORMAL (比 FULL 快，断电可能丢极少量数据，但比 Redis 安全)
        await conn.execute(text("PRAGMA synchronous=NORMAL;"))

        # 3. 加大缓存大小 (单位: 页, 1页=4KB, 这里约 100MB)
        await conn.execute(text("PRAGMA cache_size=-25000;"))

        # 4. 锁等待超时 (防止偶发锁等待报错，设置等待5秒)
        await conn.execute(text("PRAGMA busy_timeout=5000;"))

    # 创建图片数据库表 (Image)
    # 注意：这里使用的是 BaseImages
    async with engine_images.begin() as conn:
        await conn.run_sync(BaseImages.metadata.create_all)


# 依赖注入：获取会话
async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


# 获取图片数据库会话 (新增)
async def get_image_session() -> AsyncSession:
    async with image_async_session_factory() as session:
        yield session
