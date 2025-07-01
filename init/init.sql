-- Active: 1750075238811@@127.0.0.1@3306@mysql
-- MySQL 初始化数据库脚本

-- 创建数据库，明确指定字符集
CREATE DATABASE IF NOT EXISTS userdb 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE userdb;

-- 删除现有表（如果存在乱码数据）
DROP TABLE IF EXISTS users;

-- 创建用户表，明确指定字符集
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    gender VARCHAR(10) NOT NULL,
    password VARCHAR(255) NOT NULL
) ENGINE=InnoDB 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 插入一些示例用户数据
-- 注意：密码是 "password123" 的SHA256哈希值
INSERT INTO users (name, email, gender, password) VALUES 
('张三', 'zhangsan@example.com', 'male', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
('李四', 'lisi@example.com', 'male', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
('王五', 'wangwu@example.com', 'female', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
('赵六', 'zhaoliu@example.com', 'male', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
('孙七', 'sunqi@example.com', 'female', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
('周八', 'zhouba@example.com', 'male', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
('吴九', 'wujiu@example.com', 'female', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
('郑十', 'zhengshi@example.com', 'male', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
('陈十一', 'chenshiyi@example.com', 'female', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
('林十二', 'linshier@example.com', 'male', 'ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f');

-- 注意：上面的示例用户密码都是 "password123" 