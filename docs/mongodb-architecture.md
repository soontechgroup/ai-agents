# MongoDB 记忆体系统架构

## 当前状态 ⚠️ 待实现

MongoDB 已配置但暂未使用，预留给未来的记忆体系统。

## 数据职责分离

- **MySQL**：对话历史、用户、数字人配置等结构化数据 ✅
- **MongoDB**：AI 记忆、向量、知识图谱等非结构化数据 🎯

## 记忆体抽象层

已创建基础抽象接口：
- `app/core/memory/abstraction.py` - IMemory 接口
- `app/core/memory/types.py` - 记忆类型定义

具体实现待开发。