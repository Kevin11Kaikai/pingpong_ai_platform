# Phase 4: Equipment Recommendation Module

## Overview

装备推荐模块为用户提供个性化的乒乓球装备推荐服务，基于用户的打法风格、技术水平和偏好进行智能匹配。

---

## 目录

1. [模块架构](#1-模块架构)
2. [数据模型](#2-数据模型)
3. [推荐算法](#3-推荐算法)
4. [API 接口](#4-api-接口)
5. [测试方案](#5-测试方案)
6. [使用指南](#6-使用指南)
7. [常见问题](#7-常见问题)

---

## 1. 模块架构

### 1.1 目录结构

```
app/equipment_recommendation/
├── __init__.py
├── models.py              # SQLAlchemy ORM 数据库模型
├── schemas.py             # Pydantic 请求/响应模式
├── core/                  # 核心业务逻辑
│   ├── __init__.py
│   ├── equipment_service.py      # 装备/品牌/分类 CRUD
│   ├── profile_service.py        # 用户档案管理
│   ├── recommendation_engine.py  # 推荐引擎
│   └── review_service.py         # 评价管理
└── api/                   # REST API 路由
    ├── __init__.py          # Router 聚合
    ├── equipment.py         # 装备 CRUD API
    ├── brands.py            # 品牌 API
    ├── categories.py        # 分类 API
    ├── profiles.py          # 用户档案 API
    ├── recommendations.py   # 推荐 API
    └── reviews.py           # 评价 API
```

### 1.2 核心组件

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Equipment Recommendation 架构                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│   │   API 层    │    │   API 层    │    │   API 层    │             │
│   │ equipment   │    │  profiles   │    │recommendations│           │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│          │                  │                  │                     │
│          ▼                  ▼                  ▼                     │
│   ┌─────────────────────────────────────────────────────┐           │
│   │                    Core 服务层                       │           │
│   │  ┌───────────────┐  ┌───────────────┐              │           │
│   │  │EquipmentService│  │ ProfileService │              │           │
│   │  │  - CRUD 操作   │  │  - 用户档案    │              │           │
│   │  │  - 搜索/对比   │  │  - 偏好管理    │              │           │
│   │  └───────────────┘  └───────────────┘              │           │
│   │  ┌───────────────┐  ┌───────────────┐              │           │
│   │  │RecommendEngine│  │ ReviewService  │              │           │
│   │  │  - 个性化推荐  │  │  - 评价管理    │              │           │
│   │  │  - 相似推荐   │  │  - 评分统计    │              │           │
│   │  └───────────────┘  └───────────────┘              │           │
│   └─────────────────────────────────────────────────────┘           │
│                              │                                       │
│                              ▼                                       │
│   ┌─────────────────────────────────────────────────────┐           │
│   │                    数据层                            │           │
│   │  SQLite + SQLAlchemy Async + EmbeddingService       │           │
│   └─────────────────────────────────────────────────────┘           │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据模型

### 2.1 EquipmentCategory (装备分类)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(50) | 分类标识 (blade, rubber, ball, etc.) |
| display_name | String(100) | 显示名称 (底板, 胶皮, 乒乓球) |
| parent_id | FK | 父分类ID (支持层级) |
| sort_order | Integer | 排序顺序 |

### 2.2 Brand (品牌)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(100) | 品牌名 (Butterfly, DHS) |
| display_name | String(100) | 中文名 (蝴蝶, 红双喜) |
| country | String(50) | 国家 (Japan, China) |
| is_active | Boolean | 是否启用 |

### 2.3 Equipment (装备)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(255) | 装备名称 |
| brand_id | FK | 品牌ID |
| category_id | FK | 分类ID |
| price_min/max | Float | 价格范围 |
| speed_rating | Integer | 速度评分 (0-100) |
| spin_rating | Integer | 旋转评分 (0-100) |
| control_rating | Integer | 控制评分 (0-100) |
| suitable_styles | JSON | 适合打法 ["offensive", "defensive"] |
| suitable_levels | JSON | 适合水平 ["intermediate", "advanced"] |
| embedding | JSON | 向量嵌入 (用于相似度搜索) |
| avg_rating | Float | 平均评分 |
| review_count | Integer | 评价数量 |
| is_featured | Boolean | 是否精选 |

### 2.4 UserEquipmentProfile (用户偏好档案)

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | String(36) | 用户ID (unique) |
| playing_style | Enum | offensive/defensive/all_round/chopper |
| grip_style | Enum | shakehand/penhold_chinese/penhold_japanese |
| skill_level | Enum | beginner/intermediate/advanced/professional |
| prefer_speed | Integer | 速度偏好 (0-100) |
| prefer_spin | Integer | 旋转偏好 (0-100) |
| prefer_control | Integer | 控制偏好 (0-100) |
| budget_max | Float | 预算上限 |
| current_equipment | JSON | 当前使用的装备 |

### 2.5 EquipmentReview (装备评价)

| 字段 | 类型 | 说明 |
|------|------|------|
| equipment_id | FK | 装备ID |
| user_profile_id | FK | 用户档案ID |
| overall_rating | Integer | 总评分 (1-5) |
| speed_rating | Integer | 速度评分 (1-5) |
| spin_rating | Integer | 旋转评分 (1-5) |
| control_rating | Integer | 控制评分 (1-5) |
| pros/cons | JSON | 优缺点列表 |
| helpful_count | Integer | 有帮助计数 |

---

## 3. 推荐算法

### 3.1 混合推荐策略

推荐引擎采用 **规则匹配 + 向量相似度** 的混合策略，总分 = 各因素加权求和。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        推荐分数计算公式                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   总分 = 打法匹配(30%) + 水平匹配(25%) + 偏好匹配(25%) + 热度(20%)   │
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │ 1. 打法风格匹配 (权重 30%)                                    │   │
│   │    • offensive → speed×0.5 + spin×0.3 + control×0.2         │   │
│   │    • defensive → speed×0.2 + spin×0.3 + control×0.5         │   │
│   │    • all_round → speed×0.33 + spin×0.34 + control×0.33      │   │
│   │    • chopper   → speed×0.2 + spin×0.4 + control×0.4         │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │ 2. 技术水平匹配 (权重 25%)                                    │   │
│   │    • beginner     → 要求 control >= 60，推荐容错性高的装备    │   │
│   │    • intermediate → 要求 control >= 40                       │   │
│   │    • advanced     → 要求 control >= 20                       │   │
│   │    • professional → 无限制，可选择高攻击性装备                │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │ 3. 用户偏好匹配 (权重 25%)                                    │   │
│   │    • 对比 prefer_speed/spin/control 与装备评分               │   │
│   │    • 匹配度 = 1 - |用户偏好 - 装备评分| / 100                │   │
│   │    • 预算匹配检查                                            │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │ 4. 评价热度 (权重 20%)                                        │   │
│   │    • avg_rating >= 4.5 → +30%                                │   │
│   │    • avg_rating >= 4.0 → +20%                                │   │
│   │    • review_count >= 100 → +15%                              │   │
│   │    • review_count >= 50  → +10%                              │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│   精选装备额外加分: +5%                                              │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 相似装备推荐

基于向量相似度的推荐，用于"看了又看"、"同类推荐"场景。

```python
# 1. 生成装备描述的向量嵌入
text = f"{name} {description} 适合打法: {styles} 适合水平: {levels}"
embedding = EmbeddingService.encode_single(text)  # 384 维向量

# 2. 计算余弦相似度
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# 3. 在同分类装备中找最相似的 top_k 件
```

---

## 4. API 接口

### 4.1 装备管理 (`/api/equipment/equipment`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 装备列表（支持分页、筛选） |
| POST | / | 创建装备 |
| GET | /{id} | 装备详情 |
| PUT | /{id} | 更新装备 |
| DELETE | /{id} | 删除装备 |
| POST | /search | 高级搜索（多条件筛选） |
| POST | /compare | 装备对比 (2-5件) |

### 4.2 品牌管理 (`/api/equipment/brands`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 品牌列表 |
| POST | / | 创建品牌 |
| GET | /{id} | 品牌详情 |
| PUT | /{id} | 更新品牌 |
| DELETE | /{id} | 删除品牌 |

### 4.3 分类管理 (`/api/equipment/categories`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 分类列表 |
| GET | /tree | 分类树（含子分类） |
| POST | / | 创建分类 |
| GET | /{id} | 分类详情 |
| PUT | /{id} | 更新分类 |
| DELETE | /{id} | 删除分类 |

### 4.4 用户档案 (`/api/equipment/profiles`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | / | 创建用户档案 |
| GET | /user/{user_id} | 按用户ID获取 |
| GET | /{id} | 按档案ID获取 |
| PUT | /{id} | 更新档案 |
| DELETE | /{id} | 删除档案 |
| GET | /{id}/completeness | 档案完整度 |

### 4.5 智能推荐 (`/api/equipment/recommendations`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | / | 个性化推荐（需要用户档案） |
| GET | /quick | 快速推荐（无需登录） |
| POST | /similar | 相似装备推荐 |
| GET | /popular | 热门装备 |
| GET | /featured | 精选装备 |

### 4.6 评价管理 (`/api/equipment/reviews`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | / | 创建评价 |
| GET | /equipment/{id} | 装备评价列表 |
| GET | /equipment/{id}/summary | 评分汇总 |
| GET | /user/{profile_id} | 用户评价列表 |
| GET | /{id} | 评价详情 |
| PUT | /{id} | 更新评价 |
| DELETE | /{id} | 删除评价 |
| POST | /{id}/helpful | 标记有帮助 |

---

## 5. 测试方案

### 5.1 测试架构

```
scripts/
├── seed_equipment_data.py           # 初始化种子数据
└── verify_equipment_recommendation.py  # 完整验证脚本
    ├── 初始化数据（品牌、分类）
    ├── 创建示例装备
    ├── 创建测试用户档案
    ├── 测试个性化推荐
    ├── 测试相似装备推荐
    ├── 测试装备搜索和对比
    └── 测试评价功能
```

### 5.2 运行验证脚本

```bash
# 完整验证（推荐）
python scripts/verify_equipment_recommendation.py

# 详细输出
python scripts/verify_equipment_recommendation.py --verbose

# API 端点测试（需要服务器运行）
uvicorn app.main:app --reload &
python scripts/verify_equipment_recommendation.py --api-test
```

### 5.3 验证内容

#### 5.3.1 数据初始化验证

```
[Step 2] 初始化品牌数据
  ✓ 品牌总数: 6

[Step 3] 初始化分类数据
  ✓ 分类总数: 4

[Step 4] 创建示例装备
  → 创建装备: Butterfly Viscaria (速度:85, 旋转:80, 控制:70)
  → 创建装备: DHS Hurricane Long 5 (速度:92, 旋转:75, 控制:55)
  ...
  ✓ 装备总数: 8
```

#### 5.3.2 推荐合理性验证

```
[Step 6] 测试个性化推荐

  用户: 弧圈小王
  打法: offensive, 水平: intermediate, 预算: ¥600.0
  推荐结果 (3 件):
      1. DHS Hurricane 3 Neo (分数: 0.93)
         DHS | 速度:70 旋转:90 控制:70
         理由: 适合进攻型打法, 适合中级水平
      2. Butterfly Tenergy 05 (分数: 0.93)
         ...
  ✓ 推荐合理性验证通过 (平均速度:73, 平均旋转:85)
```

#### 5.3.3 验证通过标准

| 指标 | 最低要求 |
|------|---------|
| 品牌数 | >= 3 |
| 分类数 | >= 2 |
| 装备数 | >= 3 |
| 用户档案 | >= 1 |
| 推荐数 | >= 1 |
| 错误数 | = 0 |

### 5.4 单独初始化数据

```bash
# 仅初始化种子数据（品牌、分类）
python scripts/seed_equipment_data.py
```

---

## 6. 使用指南

### 6.1 快速开始

```bash
# 1. 激活环境
conda activate pingpong_ai

# 2. 初始化数据
python scripts/seed_equipment_data.py

# 3. 运行验证
python scripts/verify_equipment_recommendation.py

# 4. 启动服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6.2 API 调用示例

#### 创建用户档案

```bash
curl -X POST "http://localhost:8000/api/equipment/profiles" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "nickname": "弧圈爱好者",
    "playing_style": "offensive",
    "skill_level": "intermediate",
    "prefer_speed": 70,
    "prefer_spin": 85,
    "prefer_control": 50,
    "budget_max": 500
  }'
```

#### 获取个性化推荐

```bash
curl -X POST "http://localhost:8000/api/equipment/recommendations" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "recommendation_type": "full_setup",
    "top_k": 5
  }'
```

#### 快速推荐（无需登录）

```bash
curl "http://localhost:8000/api/equipment/recommendations/quick?\
playing_style=offensive&\
skill_level=intermediate&\
budget_max=500&\
top_k=5"
```

#### 装备搜索

```bash
curl -X POST "http://localhost:8000/api/equipment/equipment/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "弧圈",
    "suitable_styles": ["offensive"],
    "min_spin": 80,
    "page": 1,
    "page_size": 10
  }'
```

### 6.3 代码调用示例

```python
import asyncio
from app.shared.database import get_session_factory
from app.equipment_recommendation.core import (
    get_profile_service, get_recommendation_engine
)
from app.equipment_recommendation.schemas import (
    UserProfileCreate, RecommendationRequest
)

async def get_recommendations_for_user():
    session_factory = get_session_factory()
    profile_service = get_profile_service()
    engine = get_recommendation_engine()

    async with session_factory() as db:
        # 获取或创建用户档案
        profile = await profile_service.get_or_create_profile(db, "user123")

        # 获取推荐
        request = RecommendationRequest(
            user_id="user123",
            recommendation_type="blade",  # 只推荐底板
            top_k=5
        )

        items, explanation = await engine.get_recommendations(db, profile, request)

        print(f"推荐说明: {explanation}")
        for item in items:
            print(f"- {item.equipment.name} (分数: {item.score:.2f})")
            print(f"  理由: {', '.join(item.reasons)}")

asyncio.run(get_recommendations_for_user())
```

---

## 7. 常见问题

### Q1: 推荐结果为空

**原因**:
1. 数据库中没有装备数据
2. 没有符合条件的装备（预算、打法等筛选过严）

**解决**:
1. 运行 `python scripts/verify_equipment_recommendation.py` 初始化数据
2. 放宽筛选条件或增加 `budget_max`

### Q2: 推荐结果不准确

**原因**:
1. 用户档案信息不完整
2. 装备数据的 `suitable_styles/levels` 标注不准确

**解决**:
1. 完善用户档案（打法、水平、偏好）
2. 检查装备数据的标注是否正确

### Q3: 相似推荐无结果

**原因**:
1. 参考装备没有向量嵌入
2. 同分类装备数量不足

**解决**:
1. 确保装备创建时生成了 embedding
2. 添加更多同分类装备

### Q4: API 返回 422 错误

**原因**: 请求参数格式错误

**解决**: 检查 JSON 格式，确保枚举值正确：
- `playing_style`: "offensive" | "defensive" | "all_round" | "chopper"
- `skill_level`: "beginner" | "intermediate" | "advanced" | "professional"
- `grip_style`: "shakehand" | "penhold_chinese" | "penhold_japanese"

---

## 附录

### A. 种子数据

#### 品牌 (6个)
| 品牌 | 中文名 | 国家 |
|------|--------|------|
| Butterfly | 蝴蝶 | Japan |
| DHS | 红双喜 | China |
| Stiga | 斯帝卡 | Sweden |
| DONIC | 多尼克 | Germany |
| TIBHAR | 挺拔 | Germany |
| Yasaka | 亚萨卡 | Japan |

#### 分类 (4个)
| 标识 | 显示名 |
|------|--------|
| blade | 底板 |
| rubber | 胶皮 |
| ball | 乒乓球 |
| shoes | 球鞋 |

### B. 配置参数

```python
# config/settings.py
equipment_image_dir: str = "./data/uploads/equipment"
equipment_default_page_size: int = 20
equipment_max_compare_items: int = 5
equipment_recommendation_top_k: int = 5
```

### C. 依赖

- SQLAlchemy 2.0 (async)
- sentence-transformers (all-MiniLM-L6-v2)
- numpy (similarity calculation)
- FastAPI + Pydantic v2
