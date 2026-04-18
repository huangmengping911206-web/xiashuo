-- 扩展用户表，添加新字段
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- 扩展日志表，添加新字段
ALTER TABLE logs ADD COLUMN ip_address VARCHAR(45);