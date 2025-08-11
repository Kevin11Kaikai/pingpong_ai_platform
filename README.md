# 🏓 Pingpong AI Platform

A modular AI platform designed for intelligent ping pong applications — including RAG-based learning assistants, ball tracking, equipment recommendation, and social media Q&A.

---

## 📦 Project Architecture

```
pingpong_ai_platform/
├── app/
│   ├── main.py                      # FastAPI entrypoint
│   ├── routers/                    # API routers
│   │   ├── llm.py                   # LLM chat route
│   │   ├── tracking.py              # Ball tracking route
│   │   ├── equipment.py             # Equipment recommendation route
│   │   ├── social.py                # Social media Q&A route
│   │   ├── learning.py              # Learning resources route
│   │   └── analysis.py              # Real-time training analysis route
│
│   ├── LLM/                         # LLM 智能学习助手
│   │   ├── core/                    # Core RAG logic
│   │   │   ├── data_loader.py           # Load & split PDFs with OCR
│   │   │   ├── vectorstore_builder.py  # Build FAISS vectorstore
│   │   │   └── rag_chain.py             # Build RAG pipeline
│   │   ├── api/                     # API layer
│   │   │   └── chatbot.py              # Chat endpoint logic
│   │   └── config.py                   # API keys and model configs
│
│   ├── Ball_Tracking/              # 球体追踪系统
│   │   ├── core/
│   │   │   ├── yolo_detector.py        # YOLO ball detection
│   │   │   ├── trajectory_analyzer.py  # Ball trajectory analysis
│   │   │   └── speed_calculator.py     # Ball speed calculation
│   │   └── api/
│   │       └── tracking_api.py         # Tracking API endpoints
│
│   ├── Equipment_Recommendation/   # 装备推荐系统
│   │   ├── core/
│   │   │   ├── equipment_db.py         # Equipment database
│   │   │   ├── recommendation_engine.py # Recommendation algorithm
│   │   │   └── user_profile.py         # User skill level analysis
│   │   └── api/
│   │       └── recommendation_api.py   # Recommendation endpoints
│
│   ├── Social_Media/               # 社交媒体问答
│   │   ├── core/
│   │   │   ├── forum_scraper.py        # Reddit/Discourse scraper
│   │   │   ├── content_indexer.py      # Forum content indexing
│   │   │   └── hybrid_retriever.py     # AI + community data retrieval
│   │   └── api/
│   │       └── social_api.py           # Social Q&A endpoints
│
│   ├── Learning_Resources/         # 乒乓球学习资源
│   │   ├── core/
│   │   │   ├── resource_manager.py     # PDF/video resource management
│   │   │   ├── content_categorizer.py  # Content categorization
│   │   │   └── search_engine.py        # Resource search functionality
│   │   └── api/
│   │       └── resources_api.py        # Learning resources endpoints
│
│   ├── Training_Analysis/          # 实时训练分析
│   │   ├── core/
│   │   │   ├── data_processor.py       # Training data processing
│   │   │   ├── performance_analyzer.py # Performance analysis
│   │   │   ├── improvement_suggestions.py # AI-powered suggestions
│   │   │   └── real_time_monitor.py    # Real-time monitoring
│   │   └── api/
│   │       └── analysis_api.py         # Analysis endpoints
│
│   ├── data/                        # Raw data storage
│   │   ├── llm_data/                 # PDFs for vectorization
│   │   ├── ball_tracking_data/       # Video/image data
│   │   ├── equipment_data/           # Equipment specifications
│   │   ├── forum_data/               # Scraped forum content
│   │   ├── learning_resources/       # Training materials
│   │   └── training_data/            # Training session data
│
│   ├── vectorstore/                # FAISS index storage
│   │   ├── llm_index/               # LLM knowledge base
│   │   ├── forum_index/             # Forum content index
│   │   └── equipment_index/         # Equipment knowledge base
│
│   └── shared/                     # Shared utilities
│       ├── database.py              # Database connections
│       ├── auth.py                  # Authentication utilities
│       └── utils.py                 # Common utilities
│
├── frontend/                       # Frontend interface
│   ├── index.html                  # Main landing page
│   ├── css/                        # Stylesheets
│   ├── js/                         # JavaScript files
│   └── assets/                     # Images, icons, etc.
│
├── config/                         # Configuration files
│   ├── .env                        # Environment variables
│   ├── settings.py                 # Global settings
│   └── logging.py                  # Logging configuration
│
├── tests/                          # Unit and integration tests
│   ├── test_llm/                   # LLM module tests
│   ├── test_tracking/              # Ball tracking tests
│   ├── test_equipment/             # Equipment recommendation tests
│   ├── test_social/                # Social media tests
│   ├── test_learning/              # Learning resources tests
│   └── test_analysis/              # Training analysis tests
│
├── scripts/                        # Utility scripts
│   ├── setup_ocr.py                # OCR setup script
│   ├── rebuild_vectorstore.py      # Vectorstore rebuild script
│   ├── data_import.py              # Data import utilities
│   └── deployment.py               # Deployment scripts
│
├── docker/                         # Docker configuration
│   ├── Dockerfile                  # Main application Dockerfile
│   ├── docker-compose.yml          # Multi-service setup
│   └── nginx/                      # Nginx configuration
│
├── notebooks/                      # Jupyter notebooks for experiments
│   ├── llm_experiments/            # LLM RAG experiments
│   ├── tracking_experiments/       # Ball tracking experiments
│   └── analysis_experiments/       # Training analysis experiments
│
├── docs/                           # Documentation
│   ├── api/                        # API documentation
│   ├── deployment/                 # Deployment guides
│   └── user_guides/                # User guides
│
├── requirements.txt                # Python dependencies
├── requirements-dev.txt            # Development dependencies
└── README.md                       # Project documentation
```

---

## 🚀 Step-by-Step Development Plan

### 📅 总体时间安排
- **项目周期**: 12-16周
- **并行开发**: 多个模块可同时进行
- **里程碑**: 每2-3周一个可演示版本

---

### Phase 1: 基础架构搭建 (Week 1-2)
**负责人**: DevOps Engineer + Backend Engineer  
**并行任务**:
- 搭建FastAPI基础框架
- 配置Docker环境
- 建立CI/CD管道
- 设计数据库架构

**交付物**:
- `app/main.py`: FastAPI应用入口
- `docker/Dockerfile`: 容器化配置
- `config/settings.py`: 全局配置
- `shared/database.py`: 数据库连接

---

### Phase 2: LLM 智能学习助手 (Week 3-5)
**负责人**: LLM Engineer  
**协作**: Backend Engineer (API集成)

**核心任务**:
- `LLM/core/data_loader.py`: OCR scanned PDFs into LangChain Documents
- `LLM/core/vectorstore_builder.py`: Embed and store vectors with FAISS
- `LLM/core/rag_chain.py`: Create RAG pipeline using Retriever + Prompt + LLM
- `LLM/api/chatbot.py`: Chat API using FastAPI + LangChain
- `LLM/config.py`: Manage API keys and model parameters

**并行任务**:
- Content Manager: 收集和整理乒乓球PDF资料
- Frontend Developer: 设计聊天界面原型

**交付物**: 可用的RAG问答系统

---

### Phase 3: 球体追踪系统 (Week 4-6)
**负责人**: CV Engineer  
**协作**: ML Engineer (算法优化)

**核心任务**:
- `Ball_Tracking/core/yolo_detector.py`: YOLO-based ball detection
- `Ball_Tracking/core/trajectory_analyzer.py`: Ball trajectory analysis
- `Ball_Tracking/core/speed_calculator.py`: Ball speed calculation
- `Ball_Tracking/api/tracking_api.py`: Tracking API endpoints

**并行任务**:
- 让用户上传视频
- Data Engineer: 收集乒乓球视频数据
- Frontend Developer: 设计视频播放和分析界面

**交付物**: 实时球体追踪演示

---

### Phase 4: 装备推荐系统 (Week 5-7)
**负责人**: Data Engineer  
**协作**: Content Manager (装备数据整理)

**核心任务**:
- `Equipment_Recommendation/core/equipment_db.py`: Equipment database setup
- `Equipment_Recommendation/core/recommendation_engine.py`: Recommendation algorithm
- `Equipment_Recommendation/core/user_profile.py`: User skill level analysis
- `Equipment_Recommendation/api/recommendation_api.py`: Recommendation endpoints

**并行任务**:
- Content Manager: 建立装备知识库
- Frontend Developer: 设计推荐界面

**交付物**: 个性化装备推荐系统

---

### Phase 5: 社交媒体问答 (Week 6-8)
**负责人**: Backend Engineer  
**协作**: Data Engineer (数据处理)

**核心任务**:
- `Social_Media/core/forum_scraper.py`: Reddit/Discourse content scraping
- `Social_Media/core/content_indexer.py`: Forum content indexing
- `Social_Media/core/hybrid_retriever.py`: AI + community data retrieval
- `Social_Media/api/social_api.py`: Social Q&A endpoints

**并行任务**:
- Content Manager: 监控和筛选社区内容质量
- Frontend Developer: 设计社区问答界面

**交付物**: 社区内容集成系统

---

### Phase 6: 乒乓球学习资源 (Week 7-9)
**负责人**: Content Manager  
**协作**: Backend Engineer (API开发)

**核心任务**:
- `Learning_Resources/core/resource_manager.py`: PDF/video resource management
- `Learning_Resources/core/content_categorizer.py`: Content categorization
- `Learning_Resources/core/search_engine.py`: Resource search functionality
- `Learning_Resources/api/resources_api.py`: Learning resources endpoints

**并行任务**:
- Frontend Developer: 设计资源浏览界面
- LLM Engineer: 优化内容检索算法

**交付物**: 完整的资源管理系统

---

### Phase 7: 实时训练分析 (Week 8-10)
**负责人**: ML Engineer  
**协作**: CV Engineer (数据整合)

**核心任务**:
- `Training_Analysis/core/data_processor.py`: Training data processing
- `Training_Analysis/core/performance_analyzer.py`: Performance analysis
- `Training_Analysis/core/improvement_suggestions.py`: AI-powered suggestions
- `Training_Analysis/core/real_time_monitor.py`: Real-time monitoring
- `Training_Analysis/api/analysis_api.py`: Analysis endpoints

**并行任务**:
- Frontend Developer: 设计分析仪表板
- Data Engineer: 建立训练数据管道

**交付物**: AI驱动的训练分析系统

---

### Phase 8: 前端界面整合 (Week 9-11)
**负责人**: Frontend Developer  
**协作**: 所有后端工程师 (API对接)

**核心任务**:
- `frontend/index.html`: Main landing page with all modules
- `frontend/css/`: Responsive stylesheets
- `frontend/js/`: Interactive JavaScript functionality
- Connect all API endpoints using fetch/axios

**并行任务**:
- Backend Engineer: API文档和测试
- DevOps Engineer: 前端部署配置

**交付物**: 完整的用户界面

---

### Phase 9: 测试与优化 (Week 10-12)
**负责人**: 全体团队  
**分工**:
- **单元测试**: 各模块负责人
- **集成测试**: Backend Engineer
- **UI测试**: Frontend Developer
- **性能测试**: DevOps Engineer

**核心任务**:
- Add comprehensive unit tests to `tests/`
- End-to-end testing
- Performance optimization
- Security audit

**交付物**: 生产就绪的系统

---

### Phase 10: 部署与上线 (Week 11-12)
**负责人**: DevOps Engineer  
**协作**: 全体团队

**核心任务**:
- Containerize with Docker and docker-compose
- Set up CI/CD pipeline
- Deploy with Nginx configuration
- Monitor and maintain

**交付物**: 正式上线的Pingpong AI Platform

---

## 🤝 协作策略

### 周评审 (Weekly Review)


### 代码审查 (Code Review)
- **流程**: 所有代码必须经过至少一名其他团队成员审查
- **工具**: GitHub Pull Requests

### 文档同步 (Documentation Sync)
- **频率**: 每周更新
- **内容**: API文档、部署指南、用户手册

---

## 🧠 Features
- 🧠 **LLM 智能学习助手**: RAG-based Chinese PDF processing with OCR
- 🎯 **球体追踪系统**: Real-time ball tracking with YOLO + Computer Vision
- 🏓 **装备推荐系统**: Personalized equipment recommendations
- 🌐 **社交媒体问答**: Hybrid AI + community data retrieval
- 📚 **乒乓球学习资源**: Comprehensive training materials management
- 📊 **实时训练分析**: AI-powered performance analysis and suggestions
- 🔧 **模块化架构**: Each feature is self-contained and independently deployable
- 🌍 **现代化前端**: Responsive web interface for all features

---

## 🤝 Contributing
Each module is self-contained and can be developed independently. Suggested roles:

| Role              | Focus Area                   |
|-------------------|------------------------------|
| LLM Engineer      | LLM/core/, RAG pipeline      |
| CV Engineer       | Ball_Tracking/, YOLO models  |
| Data Engineer     | Equipment_Recommendation/, recommendation algorithms |
| Backend Engineer  | Social_Media/, forum integration |
| Content Manager   | Learning_Resources/, content curation |
| ML Engineer       | Training_Analysis/, performance analysis |
| Frontend Developer| frontend/, responsive UI     |
| DevOps Engineer   | docker/, deployment, CI/CD   |

---

## 📬 License & Credits
MIT License. Powered by LangChain, OpenAI, FAISS, FastAPI, and more.
