# 🏓 PingPong AI Platform

乒乓球 AI 平台 —— 基于 FastAPI 构建的可拓展聊天机器人 MVP，预计支持论坛、器材评测、教学视频和资讯模块。

---

## 🧩 项目背景

我们希望打造一个“乒乓球垂直领域”平台，起步以 AI Chatbot 为核心，后续融入论坛交流、器材评测、教学视频、八卦/资讯等功能。采用 MVP（最小可实现系统）策略，先实现核心，逐步扩展。

---

## 🚀 技术栈

- **后端**：Python + FastAPI  
- **异步**：原生 async/await  
- **数据验证**：Pydantic  
- **文档生成**：自动生成 OpenAPI / Swagger UI  
- **数据库**：（后续）SQLModel + Alembic + PostgreSQL  
- **可选**：MCP 支持、WebSocket、背景任务等  

---

## ⚙️ 项目结构

pingpong_ai_platform/
├── app/
│ ├── main.py # 应用入口
│ ├── core/
│ │ ├── config.py # 环境配置
│ │ └── database.py # 数据库连接管理
│ ├── routers/ # 路由分层（chatbot、forum 等）
│ ├── services/ # 核心业务逻辑（如 Chatbot）
│ ├── repositories/ # 数据存储接口
│ └── utils/ # 日志、工具函数等
├── tests/ # 单元/集成测试
├── alembic/ # 数据库迁移脚本
├── Dockerfile
├── docker-compose.yml
├── .env
└── README.md

---

## 💬 如何使用

1. 克隆仓库
2. 创建 `.env`，配置 OPENAI_API_KEY、数据库 URL 等
3. 安装依赖：`pip install -r requirements.txt`
4. 启动服务：`uvicorn app.main:app --reload`
5. 打开浏览器访问 `http://localhost:8000/docs` 查看 API 文档
6. 测试 Chatbot 接口：
   ```bash
   POST /chatbot/ask
   {
     "user_input": "你好，如何提高发球？"
   }

