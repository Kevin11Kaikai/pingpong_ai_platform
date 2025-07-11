# 🏓 Pingpong AI Platform

A modular AI platform designed for intelligent ping pong applications — including RAG-based learning assistants, ball tracking, equipment recommendation, and social media Q&A.

---

## 📦 Project Architecture

```
pingpong_ai_platform/
├── app/
│   ├── main.py                      # FastAPI entrypoint
│   ├── routers/                    # API routers
│   │   ├── chat.py                  # LLM chat route
│   │   ├── tracking.py              # Ball tracking route
│   │   └── equipment.py             # Equipment recommendation route
│
│   ├── LLM/                         # Language model RAG pipeline
│   │   ├── core/                    # Core logic
│   │   │   ├── data_loader.py           # Load & split PDFs
│   │   │   ├── vectorstore_builder.py  # Build FAISS vectorstore
│   │   │   └── rag_chain.py             # Build RAG chain
│   │   ├── api/                     # API layer
│   │   │   └── chatbot.py              # Chat endpoint logic
│   │   └── config.py                   # API keys and path configs
│
│   ├── Ball_Tracking/              # Ping pong ball tracking (YOLO + CV)
│   │   └── ball_tracking.py
│
│   ├── Social_Media/               # Social Q&A/forum extensions
│   ├── Equipment_Recommendation/   # Equipment suggestions
│   ├── Pingpong_Learning_Resource/ # Training PDFs, videos, FAQ
│
│   ├── data/                        # Raw data
│   │   ├── LLM_data/                # PDFs for vectorization
│   │   └── ball_tracking_data/
│
│   └── vectorstore/                # FAISS index storage
│
├── index.html                      # Frontend web interface for testing (HTML)
├── config/                         # .env and global config
├── tests/                          # Unit tests
├── scripts/                        # Init scripts (OCR, vectorstore rebuild)
├── docker/                         # Docker/Docker-compose for deployment
├── notebooks/                      # Jupyter experiments
├── requirements.txt                # Python deps
└── README.md
```

---

## 🚀 Step-by-Step Development Plan

### Phase 1: RAG Core
- `data_loader.py`: OCR scanned PDFs into LangChain Documents
- `vectorstore_builder.py`: Embed and store vectors with FAISS
- `rag_chain.py`: Create RAG pipeline using Retriever + Prompt + LLM
- `chatbot.py`: Chat API using FastAPI + LangChain
- `config.py`: Manage API keys and model parameters

### Phase 2: Backend Integration
- `main.py` + `routers/chat.py`: Route and mount `/chat` API

### Phase 3: Add Ball Tracking and Equipment Suggestion
- `Ball_Tracking/ball_tracking.py`: Track and analyze ball movement
- `Equipment_Recommendation/`: Build equipment knowledge base

### Phase 4: Forum Integration
- Ingest content from forums (Reddit, Discourse, etc.)
- Index and allow hybrid retrieval across LLM + community data

### Phase 5: Frontend Testing Site
- `index.html`: Create a basic UI for testing chat and demo features
- Connect to `/chat` API endpoint using fetch/axios

### Phase 6: Testing & Deployment
- Add unit tests to `tests/`
- Containerize with Docker
- Automate batch PDF parsing with `scripts/`

---

## 🧠 Features
- ✅ RAG for scanned Chinese PDFs (via OCR)
- ✅ Vector database with FAISS
- ✅ Chat endpoint via FastAPI
- 🏓 Real-time ball tracking (YOLO-based)
- 🎓 Training content Q&A (PDFs, videos)
- 🤖 Equipment recommendation
- 🌐 Extendable social/forum Q&A
- 🌍 Basic HTML interface for public demo

---

## 🤝 Contributing
Each module is self-contained and can be developed independently. Suggested roles:

| Role              | Focus Area                   |
|-------------------|------------------------------|
| RAG Engineer      | LLM/core/, chatbot.py        |
| Backend Engineer  | main.py, routers/, API glue  |
| CV Engineer       | Ball_Tracking/, image models |
| Forum Engineer    | Social_Media/, data ingestion|
| UI Developer      | index.html, frontend UX      |

---

## 📬 License & Credits
MIT License. Powered by LangChain, OpenAI, FAISS, FastAPI, and more.
