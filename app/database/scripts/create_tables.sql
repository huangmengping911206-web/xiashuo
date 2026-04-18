-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100)
);

-- 创建日志表
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_time TIMESTAMP NOT NULL,
    user_name VARCHAR(50),
    url TEXT,
    method VARCHAR(10),
    result_code VARCHAR(3),
    result_msg TEXT,
    spend_time VARCHAR(20)
);