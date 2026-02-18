# Phase 4: Equipment Recommendation Module

## Overview

装备推荐模块为用户提供个性化的乒乓球装备推荐服务，基于用户的打法风格、技术水平和偏好进行智能匹配。

## Module Architecture

```
app/equipment_recommendation/
├── __init__.py
├── models.py              # SQLAlchemy ORM models
├── schemas.py             # Pydantic request/response schemas
├── core/
│   ├── __init__.py
│   ├── equipment_service.py      # 装备/品牌/分类 CRUD
│   ├── profile_service.py        # 用户档案管理
│   ├── recommendation_engine.py  # 推荐引擎
│   └── review_service.py         # 评价管理
└── api/
    ├── __init__.py          # Router aggregation
    ├── equipment.py         # 装备 CRUD API
    ├── brands.py            # 品牌 API
    ├── categories.py        # 分类 API
    ├── profiles.py          # 用户档案 API
    ├── recommendations.py   # 推荐 API
    └── reviews.py           # 评价 API
```

## Data Models

### EquipmentCategory (装备分类)
| Field | Type | Description |
|-------|------|-------------|
| id | String(36) | UUID |
| name | String(50) | 分类标识 (blade, rubber, ball, etc.) |
| display_name | String(100) | 显示名称 |
| parent_id | FK | 父分类ID (支持层级) |

### Brand (品牌)
| Field | Type | Description |
|-------|------|-------------|
| id | String(36) | UUID |
| name | String(100) | 品牌名 (Butterfly, DHS) |
| display_name | String(100) | 中文名 |
| country | String(50) | 国家 |

### Equipment (装备)
| Field | Type | Description |
|-------|------|-------------|
| id | String(36) | UUID |
| name | String(255) | 装备名称 |
| brand_id | FK | 品牌ID |
| category_id | FK | 分类ID |
| speed_rating | Integer | 速度评分 (0-100) |
| spin_rating | Integer | 旋转评分 (0-100) |
| control_rating | Integer | 控制评分 (0-100) |
| suitable_styles | JSON | 适合打法 ["offensive", "defensive"] |
| suitable_levels | JSON | 适合水平 ["intermediate", "advanced"] |
| embedding | JSON | 向量嵌入 (用于相似度搜索) |

### UserEquipmentProfile (用户偏好档案)
| Field | Type | Description |
|-------|------|-------------|
| user_id | String(36) | 用户ID (unique) |
| playing_style | Enum | offensive/defensive/all_round/chopper |
| grip_style | Enum | shakehand/penhold_chinese/penhold_japanese |
| skill_level | Enum | beginner/intermediate/advanced/professional |
| prefer_speed | Integer | 速度偏好 (0-100) |
| prefer_spin | Integer | 旋转偏好 (0-100) |
| prefer_control | Integer | 控制偏好 (0-100) |
| budget_max | Float | 预算上限 |

### EquipmentReview (装备评价)
| Field | Type | Description |
|-------|------|-------------|
| equipment_id | FK | 装备ID |
| overall_rating | Integer | 总评分 (1-5) |
| pros/cons | JSON | 优缺点列表 |

## API Endpoints

### Equipment (`/api/equipment/equipment`)
| Method | Path | Description |
|--------|------|-------------|
| GET | / | 装备列表 |
| POST | / | 创建装备 |
| GET | /{id} | 装备详情 |
| PUT | /{id} | 更新装备 |
| DELETE | /{id} | 删除装备 |
| POST | /search | 高级搜索 |
| POST | /compare | 装备对比 (2-5件) |

### Brands (`/api/equipment/brands`)
| Method | Path | Description |
|--------|------|-------------|
| GET | / | 品牌列表 |
| POST | / | 创建品牌 |
| GET/PUT/DELETE | /{id} | 品牌 CRUD |

### Categories (`/api/equipment/categories`)
| Method | Path | Description |
|--------|------|-------------|
| GET | / | 分类列表 |
| GET | /tree | 分类树 |
| POST/GET/PUT/DELETE | /{id} | 分类 CRUD |

### Profiles (`/api/equipment/profiles`)
| Method | Path | Description |
|--------|------|-------------|
| POST | / | 创建用户档案 |
| GET | /user/{user_id} | 按用户ID获取 |
| PUT | /{id} | 更新档案 |
| GET | /{id}/completeness | 档案完整度 |

### Recommendations (`/api/equipment/recommendations`)
| Method | Path | Description |
|--------|------|-------------|
| POST | / | 个性化推荐 |
| GET | /quick | 快速推荐 (无需登录) |
| POST | /similar | 相似装备推荐 |
| GET | /popular | 热门装备 |
| GET | /featured | 精选装备 |

### Reviews (`/api/equipment/reviews`)
| Method | Path | Description |
|--------|------|-------------|
| POST | / | 创建评价 |
| GET | /equipment/{id} | 装备评价列表 |
| GET | /equipment/{id}/summary | 评分汇总 |
| POST | /{id}/helpful | 标记有帮助 |

## Recommendation Algorithm

### 混合推荐策略
推荐引擎采用 **规则匹配 + 向量相似度** 的混合策略：

1. **打法风格匹配 (30%)**
   - 进攻型: speed 50%, spin 30%, control 20%
   - 防守型: speed 20%, spin 30%, control 50%
   - 全面型: 均衡分配

2. **技术水平匹配 (25%)**
   - 初学者: 要求 control >= 60, 推荐容错性高的装备
   - 专业级: 无限制, 可选择高攻击性装备

3. **用户偏好匹配 (25%)**
   - 对比用户的 prefer_speed/spin/control 与装备评分
   - 预算匹配

4. **评价热度 (20%)**
   - avg_rating >= 4.5: +30%
   - review_count >= 100: +15%

### 相似装备推荐
- 使用 `all-MiniLM-L6-v2` 生成装备描述的向量嵌入
- 余弦相似度匹配同分类装备

## Seed Data

运行 `python scripts/seed_equipment_data.py` 初始化：

### Categories (6个)
- blade (底板), rubber (胶皮), ball (乒乓球)
- shoes (球鞋), apparel (服装), accessories (配件)

### Brands (12个)
- 日本: Butterfly, Yasaka, Nittaku
- 德国: DONIC, TIBHAR, JOOLA
- 中国: DHS, 729, Yinhe, Double Fish
- 其他: Stiga (瑞典), Xiom (韩国)

## Configuration

```python
# config/settings.py
equipment_image_dir: str = "./data/uploads/equipment"
equipment_default_page_size: int = 20
equipment_max_compare_items: int = 5
equipment_recommendation_top_k: int = 5
```

## Test Results

API 测试验证通过：
- 品牌列表: 12 个品牌
- 分类列表: 6 个分类
- 用户档案创建: 成功创建进攻型中级用户
- 个性化推荐: 返回匹配的装备 (DHS Hurricane 3 Neo, Butterfly Tenergy 05 等)
- 推荐结果合理，高旋转胶皮排名靠前，符合用户偏好

## Dependencies

- SQLAlchemy 2.0 (async)
- sentence-transformers (embedding)
- numpy (similarity calculation)
