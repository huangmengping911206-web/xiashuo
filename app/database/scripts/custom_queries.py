from sqlalchemy.sql import text
from app.database.session import engine
from pathlib import Path


def execute_sql_file(file_name: str):
    sql_path = Path(f"app/database/scripts/{file_name}")
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file {file_name} not found")

    with open(sql_path, "r") as f:
        sql = f.read()

    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()


def init_tables():
    execute_sql_file("create_tables.sql")


def extend_tables():
    execute_sql_file("alter_tables.sql")