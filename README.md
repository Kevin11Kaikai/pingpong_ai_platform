# Pingpong AI Platform

An modular AI platform for table tennis, combining LLM-powered coaching, computer vision ball tracking, equipment recommendation, and training analysis into a single deployable system.

**Hardware**: NVIDIA RTX 4080 Super (16GB VRAM) | **Backend**: FastAPI | **LLM**: OpenAI API (gpt-4o-mini) | **CV**: BlurBall + TT3D

---

## Features

| Module | Description | Key Tech |
|--------|-------------|----------|
| **LLM Learning Assistant** | RAG-based Q&A on table tennis knowledge (PDF ingestion, conversation history, streaming) | OpenAI API, FAISS, sentence-transformers |
| **Ball Tracking** | Upload match video → 2D detection → 3D trajectory reconstruction → bounce/spin analysis | BlurBall (HRNet-W48), TT3D, OpenCV |
| **Equipment Recommendation** | Personalized gear recommendations based on player profile, style, and budget | Embedding similarity, rule filtering, LLM-generated explanations |
| **Social Media Q&A** | Scrape and index table tennis communities, hybrid retrieval (semantic + keyword) | BeautifulSoup, FAISS, BM25 |
| **Learning Resources** | Curriculum management, progress tracking, adaptive recommendations | Knowledge graph, spaced repetition |
| **Training Analysis** | Session logging, goal tracking, AI-driven insights on performance trends | Statistical analysis, LLM insights |

## Architecture

```
                          ┌─────────────────────────────┐
                          │      Nginx (:80)            │
                          │  Reverse Proxy / Rate Limit │
                          └──────────┬──────────────────┘
                                     │
                          ┌──────────▼──────────────────┐
                          │   FastAPI + Uvicorn (:8000)  │
                          │                              │
                          │  ┌────────┐  ┌────────────┐ │
                          │  │  LLM   │  │Ball Tracking│ │
                          │  │  /api/  │  │  /api/     │ │
                          │  │  llm/   │  │ball-tracking│ │
                          │  └────────┘  └────────────┘ │
                          │  ┌────────┐  ┌────────────┐ │
                          │  │Equip-  │  │  Social    │ │
                          │  │ment    │  │  Media     │ │
                          │  └────────┘  └────────────┘ │
                          │  ┌────────┐  ┌────────────┐ │
                          │  │Learning│  │  Training  │ │
                          │  │Resource│  │  Analysis  │ │
                          │  └────────┘  └────────────┘ │
                          │                              │
                          │  Shared: Database │ GPU Mgr  │
                          │  Embedding │ Auth │ Metrics  │
                          └──────────┬──────────────────┘
                                     │
                     ┌───────────────┼───────────────┐
                     ▼               ▼               ▼
              ┌────────────┐ ┌────────────┐ ┌────────────┐
              │ Prometheus │ │  Grafana   │ │  SQLite    │
              │  (:9090)   │ │  (:3000)   │ │  + FAISS   │
              └────────────┘ └────────────┘ └────────────┘
```

## Quick Start

### Prerequisites

- Docker Desktop 29+ with WSL2 backend
- NVIDIA GPU with driver 535+ (for ball tracking / CV features)
- LLM API key (OpenAI-compatible endpoint)

### 1. Clone and configure

```bash
git clone https://github.com/Kevin11Kaikai/pingpong_ai_platform.git -b PingPong_2026
cd pingpong_ai_platform

cp .env.production.example .env.production
# Edit .env.production: set LLM_API_KEY, JWT_SECRET_KEY, GRAFANA_ADMIN_PASSWORD
```

### 2. Build and run

```bash
docker compose -f docker/docker-compose.prod.yml build pingpong-api
docker compose -f docker/docker-compose.prod.yml up -d
```

First build takes ~15 minutes (downloads CUDA base image + PyTorch + dependencies). Subsequent code-only rebuilds take seconds thanks to layer caching.

### 3. Verify

```bash
# Check all containers are healthy
docker ps --format "table {{.Names}}\t{{.Status}}"

# Test API
curl http://localhost/api/health/
# {"status":"healthy","version":"0.1.0"}

# Test LLM chat
curl -X POST http://localhost/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What are the key techniques in forehand topspin?","conversation_id":null}'
```

### Access Points

| Service | URL |
|---------|-----|
| Web UI | http://localhost |
| API Docs (Swagger) | http://localhost:8001/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

## Local Development (without Docker)

```bash
# Requires: conda, Python 3.11, NVIDIA GPU + CUDA 12.4
conda create -n pingpong_ai python=3.11 -y
conda activate pingpong_ai

pip install -r requirements.txt
pip install -r requirements-gpu.txt

cp .env.example .env
# Edit .env with your configuration

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
pingpong_ai_platform/
├── app/                          # Backend application
│   ├── main.py                   # FastAPI entrypoint + router registration
│   ├── api/                      # Shared API (health checks)
│   ├── llm/                      # LLM learning assistant module
│   │   ├── api/                  #   Chat, conversations, documents endpoints
│   │   └── core/                 #   RAG service, LLM client, vector store
│   ├── ball_tracking/            # Ball tracking module
│   │   ├── api/                  #   Upload, jobs, visualization endpoints
│   │   └── core/                 #   Detector, tracker, trajectory analyzer
│   ├── equipment_recommendation/ # Equipment recommendation module
│   │   ├── api/                  #   Equipment, profiles, reviews endpoints
│   │   └── core/                 #   Recommendation engine, review service
│   ├── social_media/             # Social media Q&A module
│   │   ├── api/                  #   Content, scraping endpoints
│   │   └── core/                 #   Scraper, content service
│   ├── learning_resources/       # Learning resources module
│   │   ├── api/                  #   Resources, progress, recommendations
│   │   └── core/                 #   Curriculum, knowledge, profile services
│   ├── training_analysis/        # Training analysis module
│   │   ├── api/                  #   Sessions, goals, insights endpoints
│   │   └── core/                 #   Analysis, metrics, insight services
│   └── shared/                   # Shared utilities
│       ├── database.py           #   Async SQLAlchemy + SQLite
│       ├── gpu_manager.py        #   GPU memory lifecycle management
│       ├── embedding.py          #   Shared sentence-transformers model
│       ├── health.py             #   Component health checks
│       └── metrics.py            #   Prometheus metrics middleware
├── frontend/                     # Web UI (vanilla HTML/CSS/JS)
│   ├── index.html                #   Dashboard
│   ├── pages/                    #   6 module pages (chat, video, equipment, ...)
│   ├── css/                      #   Stylesheets
│   └── js/                       #   API clients, components, page logic
├── config/                       # Configuration
│   ├── settings.py               #   Pydantic settings (from .env)
│   └── logging.py                #   Loguru setup
├── docker/                       # Docker deployment
│   ├── Dockerfile.prod           #   Multi-stage build (CUDA + Python)
│   ├── docker-compose.prod.yml   #   4-service orchestration
│   ├── nginx/nginx.conf          #   Reverse proxy config
│   └── prometheus/prometheus.yml #   Metrics scraping config
├── tests/                        # Test suite (357 test cases)
│   ├── conftest.py               #   Shared fixtures
│   ├── test_llm.py               #   LLM module tests
│   ├── test_ball_tracking.py     #   Ball tracking tests
│   ├── test_equipment.py         #   Equipment tests
│   ├── test_social_media.py      #   Social media tests
│   ├── test_learning_resources.py#   Learning resources tests
│   ├── test_training_analysis.py #   Training analysis tests
│   ├── test_integration.py       #   Cross-module integration tests
│   ├── test_e2e.py               #   End-to-end API tests
│   └── test_infrastructure.py    #   Infrastructure tests
├── documents/                    # Phase documentation
├── external/                     # External repos (BlurBall, TT3D)
├── scripts/                      # Utility scripts
├── .github/workflows/            # CI/CD (test, build, deploy)
├── CLAUDE.md                     # AI assistant project context
├── requirements.txt              # Python dependencies
└── requirements-gpu.txt          # PyTorch + CUDA dependencies
```

## API Overview

191 routes across 6 modules + health/metrics.

| Prefix | Module | Key Endpoints |
|--------|--------|---------------|
| `/api/health/` | Health | `GET /` `GET /full` `GET /ready` `GET /live` |
| `/api/llm/` | LLM | `POST /chat` `POST /chat/stream` `POST /search` `CRUD /conversations` `CRUD /documents` |
| `/api/ball-tracking/` | Ball Tracking | `POST /upload` `GET /jobs/{id}/status` `GET /jobs/{id}/result` `POST /jobs/{id}/visualize` |
| `/api/equipment/` | Equipment | `CRUD /equipment` `POST /recommendations` `CRUD /reviews` `CRUD /brands` `CRUD /categories` |
| `/api/social-media/` | Social Media | `CRUD /contents` `POST /scrape` `GET /search` |
| `/api/learning/` | Learning | `CRUD /resources` `GET /knowledge` `CRUD /profiles` `CRUD /enrollments` `GET /recommendations` |
| `/api/training/` | Training | `CRUD /sessions` `CRUD /goals` `GET /analysis` `GET /insights` `GET /metrics` |

Full interactive documentation available at `/docs` (Swagger UI) when running.

## GPU Memory Management

The platform carefully manages GPU memory to run multiple AI models on a single 16GB GPU:

- **CV models load serially**: BlurBall → RTMPose → MotionBert (never simultaneously)
- **LLM uses cloud API**: Zero local GPU memory
- **Embedding model**: ~0.5GB, shared across LLM/Equipment/Social modules
- **Auto-cleanup**: `torch.cuda.empty_cache()` after each inference
- **GPUManager**: Centralized model lifecycle management in `app/shared/gpu_manager.py`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Uvicorn, SQLAlchemy (async), Pydantic |
| LLM | OpenAI API (gpt-4o-mini), sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | FAISS (CPU mode) |
| CV | BlurBall (HRNet-W48), OpenCV, PyTorch |
| Database | SQLite + aiosqlite |
| Frontend | Vanilla HTML/CSS/JS, Chart.js |
| Auth | JWT (python-jose) |
| Deployment | Docker, Nginx, Prometheus, Grafana |
| CI/CD | GitHub Actions |
| GPU | CUDA 12.4, NVIDIA RTX 4080 Super |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific module tests
pytest tests/test_llm.py -v
pytest tests/test_ball_tracking.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

357 test cases across 10 test files covering unit, integration, and end-to-end scenarios.

## Monitoring

With Docker deployment, Prometheus and Grafana are included:

- **Prometheus** (`:9090`): Scrapes `/metrics` from the API every 10 seconds
- **Grafana** (`:3000`): Dashboards for request rates, latencies, GPU utilization, error rates
- **Health endpoints**: `/api/health/full` returns component-level status (database, GPU, embedding)

## Documentation

| Document | Description |
|----------|-------------|
| [Phase 3: Ball Tracking](documents/phase3_ball_tracking_guide.md) | BlurBall + TT3D integration guide |
| [Phase 4: Equipment](documents/phase4_equipment_recommendation.md) | Recommendation system design |
| [Phase 5: Social Media](documents/phase5_social_media.md) | Scraping and RAG pipeline |
| [Phase 6: Learning Resources](documents/phase6_learning_resources_guide.md) | Curriculum and progress system |
| [Phase 7: Training Analysis](documents/phase7_training_analysis_guide.md) | Session and insights system |
| [Phase 8: Frontend](documents/phase8_frontend_guide.md) | UI architecture and pages |
| [Phase 9: Testing](documents/phase9_testing.md) | Test strategy and coverage |
| [Phase 10: Deployment](documents/phase10_deployment.md) | Production deployment guide |
| [Windows Docker Guide](documents/windows_docker_desktop.md) | Local deployment on Windows + Docker Desktop |

## Project Stats

| Metric | Value |
|--------|-------|
| Backend Python files | 101 |
| Backend lines of code | ~19,000 |
| Frontend files | 34 |
| Frontend lines of code | ~8,800 |
| API routes | 191 |
| Test cases | 357 |
| Frontend pages | 7 (dashboard + 6 modules) |
| Docker services | 4 (API, Nginx, Prometheus, Grafana) |

## License

This project is for educational and research purposes.

## References

- [BlurBall](https://github.com/cogsys-tuebingen/BlurBall) - Motion-blur aware ball detection
- [TT3D](https://github.com/cogsys-tuebingen/tt3d) - 3D trajectory reconstruction for table tennis
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [sentence-transformers](https://www.sbert.net/) - Text embeddings
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search
