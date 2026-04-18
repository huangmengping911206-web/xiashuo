from sqlalchemy import text

# 定义需要自动修补的表结构变更
# 格式：(表名, 列名, 列类型定义, 默认值)
from app.core.logging import logger

AUTO_MIGRATIONS = [
    ("users", "avatar_id", "INTEGER", "NULL"),
    ("users", "settings", "TEXT", "NULL"),
    ("tweets", "image_ids", "TEXT", "NULL"),  # 示例：后续新增的字段
    ("messages", "type", "TEXT", "text"),  # 示例：后续新增的字段
]


async def run_safe_migrations(engine):
    """
    启动时自动执行安全的数据库迁移（仅添加缺失列）
    """
    logger.info("检查数据库结构更新...")

    async with engine.begin() as conn:
        for table, column, col_type, default in AUTO_MIGRATIONS:
            try:
                # 1. 检查列是否已存在
                # SQLite 的 PRAGMA table_info 返回表结构信息
                result = await conn.execute(text(f"PRAGMA table_info({table})"))
                columns = [row[1] for row in result.fetchall()]

                if column not in columns:
                    # 2. 不存在则添加
                    logger.info(f"检测到缺失字段: {table}.{column}，正在自动添加...")

                    # 拼接 SQL (注意：SQLite ALTER TABLE 只能加列，不能改列)
                    sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}"
                    await conn.execute(text(sql))

                    logger.success(f"字段 {table}.{column} 添加成功")
            except Exception as e:
                logger.error(f"自动迁移失败 {table}.{column}: {e}")
                # 即使失败也不要阻断启动，生产环境通常会记录日志后继续
