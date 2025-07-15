# 系统架构设计

## 系统整体架构

```mermaid
graph TB
    subgraph "前端层"
        Frontend["ai-agents-frontend<br/>用户端前端<br/>⚠️ 待实现"]
        Admin["ai-agents-admin<br/>管理后台前端<br/>✅ 基础认证已实现"]
    end
    
    subgraph "部署平台"
        Vercel["Vercel<br/>前端托管"]
    end
    
    subgraph "后端层"
        Backend["ai-agents<br/>后端服务<br/>✅ 用户认证API"]
    end
    
    subgraph "数据层"
        DB[("MySQL 8.0<br/>✅ 已实现")]
        Cache[("Redis<br/>⚠️ 待实现")]
        MQ["消息队列<br/>⚠️ 待实现"]
    end
    
    User[用户] --> Vercel
    Vercel --> Admin
    Frontend -.->|未实现| Backend
    Admin -->|HTTPS| Backend
    
    Backend --> DB
    Backend -.->|未实现| Cache
    Backend -.->|未实现| MQ
    
    style User fill:#f9f,stroke:#333,stroke-width:2px
    style Frontend fill:#e0e0e0,stroke:#9e9e9e,color:#666,stroke-dasharray: 5 5
    style Admin fill:#34a853,stroke:#2e7d32,color:#fff
    style Vercel fill:#000,stroke:#000,color:#fff
    style Backend fill:#ea4335,stroke:#c5221f,color:#fff
    style DB fill:#fbbc04,stroke:#f9ab00
    style Cache fill:#e0e0e0,stroke:#9e9e9e,color:#666,stroke-dasharray: 5 5
    style MQ fill:#e0e0e0,stroke:#9e9e9e,color:#666,stroke-dasharray: 5 5
```

## 架构说明

### 1. 前端层

#### ai-agents-admin（管理后台）✅ 已实现
- **技术栈**：Next.js 14 + React 18 + TypeScript + Tailwind CSS
- **部署方式**：Vercel
- **已实现功能**：
  - 用户注册（/register）
  - 用户登录（/login）
  - 主页面板（/）
- **待实现功能** ⚠️：
  - AI 代理管理
  - 数据统计

#### ai-agents-frontend（用户端）⚠️ 待实现
- **技术栈**：待定
- **部署方式**：待定
- **主要功能**：用户交互界面

### 2. 后端层

#### ai-agents（API服务）
- **技术栈**：FastAPI + SQLAlchemy 2.0 + Pydantic
- **架构模式**：分层架构（Controller → Service → Repository）
- **认证方式**：JWT
- **已实现接口**：
  - POST `/api/v1/auth/register` - 用户注册
  - POST `/api/v1/auth/login` - 用户登录
  - GET `/api/v1/auth/me` - 获取当前用户信息
- **待实现接口** ⚠️：
  - AI 代理管理 API
  - 其他业务接口

### 3. 数据层

#### 数据库
- **类型**：MySQL 8.0
- **ORM**：SQLAlchemy 2.0
- **特性**：支持自动建表（AutoMigrate）

#### 缓存 ⚠️ 待实现
- **类型**：Redis
- **用途**：会话管理、热点数据缓存

#### 消息队列 ⚠️ 待实现
- **类型**：RabbitMQ/Kafka
- **用途**：异步任务处理、事件驱动

## 部署架构

```mermaid
graph LR
    subgraph "Vercel"
        Admin["ai-agents-admin<br/>Next.js App"]
    end
    
    subgraph "云服务器"
        Backend["ai-agents<br/>FastAPI Service"]
        DB[(MySQL 8.0)]
    end
    
    subgraph "CDN"
        Static["静态资源"]
    end
    
    User[用户] --> Vercel
    Vercel --> Backend
    Backend --> DB
    Vercel --> Static
    
    style User fill:#f9f,stroke:#333,stroke-width:2px
    style Vercel fill:#000,stroke:#000,color:#fff
    style Backend fill:#009688,stroke:#00695c,color:#fff
    style DB fill:#ff9800,stroke:#e65100,color:#fff
    style Static fill:#2196f3,stroke:#0d47a1,color:#fff
```

### 部署说明

#### 前端部署（Vercel）
1. **自动部署**：通过 GitHub 集成，推送代码自动触发部署
2. **环境变量**：
   ```
   NEXT_PUBLIC_API_URL=https://api.yourdomain.com
   ```
3. **构建配置**：
   - Build Command: `npm run build`
   - Output Directory: `.next`
   - Install Command: `npm install`
4. **域名配置**：支持自定义域名绑定

#### 后端部署
1. **部署方式**：Docker 容器化部署
2. **反向代理**：Nginx
3. **进程管理**：Supervisor/PM2
4. **环境配置**：通过环境变量管理不同环境

### 环境划分

| 环境 | 前端域名 | 后端API | 数据库 |
|------|---------|---------|--------|
| 开发 | localhost:3000 | localhost:8000 | ai_agents_dev |
| 测试 | test.yourdomain.com | api-test.yourdomain.com | ai_agents_test |
| 预发布 | staging.yourdomain.com | api-staging.yourdomain.com | ai_agents_staging |
| 生产 | app.yourdomain.com | api.yourdomain.com | ai_agents |