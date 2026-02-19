# Phase 9: 测试套件文档

## 测试架构总览

本项目采用 pytest 框架构建了完整的测试套件，覆盖所有 6 个核心模块。

### 测试统计

| 指标 | 数值 |
|------|------|
| 测试文件数 | 9 |
| 测试用例总数 | 357 |
| 通过 | 355 |
| 跳过 | 2 |
| 警告 | 3 |
| 执行时间 | ~17 秒 |

### 测试文件结构

```
tests/
├── __init__.py
├── conftest.py              # 共享 fixtures
├── test_infrastructure.py   # 基础设施测试
├── test_llm.py              # LLM/RAG 模块测试
├── test_ball_tracking.py    # 球体追踪模块测试
├── test_social_media.py     # 社交媒体模块测试
├── test_learning_resources.py # 学习资源模块测试
├── test_training_analysis.py  # 训练分析模块测试
├── test_equipment.py        # 装备推荐模块测试
├── test_integration.py      # 集成测试
└── test_e2e.py              # 端到端测试
```

## 测试覆盖表

| 模块 | 测试文件 | 测试数 | 覆盖范围 |
|------|----------|--------|----------|
| Infrastructure | `test_infrastructure.py` | 16 | 配置加载、GPU 管理、Embedding 服务、数据库连接 |
| LLM/RAG | `test_llm.py` | 22 | LLM 客户端、向量存储、RAG 检索、聊天 API |
| Ball Tracking | `test_ball_tracking.py` | 28 | 视频处理、轨迹检测、分析服务、可视化 |
| Social Media | `test_social_media.py` | 36 | 内容抓取、情感分析、回复生成、平台配置 |
| Learning Resources | `test_learning_resources.py` | 51 | 资源管理、学习路径、进度跟踪、知识点 |
| Training Analysis | `test_training_analysis.py` | 23 | 训练会话、目标管理、AI 洞察、统计分析 |
| Equipment | `test_equipment.py` | 79 | 品牌/分类/装备 CRUD、推荐引擎、评价系统 |
| Integration | `test_integration.py` | 17 | 跨模块数据流、嵌入服务共享、API 一致性 |
| E2E | `test_e2e.py` | 19 | 用户注册流程、装备推荐流程、学习旅程 |

### test_equipment.py 详细覆盖

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|----------|
| TestBrandSchemas | 4 | 品牌创建/更新 Schema 验证 |
| TestCategorySchemas | 3 | 分类创建 Schema 验证 |
| TestEquipmentSchemas | 9 | 装备创建/搜索/对比 Schema 验证 |
| TestUserProfileSchemas | 3 | 用户档案 Schema 验证 |
| TestReviewSchemas | 3 | 评价 Schema 验证 |
| TestRecommendationSchemas | 2 | 推荐请求 Schema 验证 |
| TestModelEnums | 6 | 枚举值、ORM 模型表示 |
| TestEquipmentService | 14 | 品牌/分类/装备 CRUD、搜索、对比 |
| TestProfileService | 4 | 用户档案 CRUD、完整度计算 |
| TestReviewService | 2 | 评价创建、标记有帮助 |
| TestRecommendationEngine | 5 | 风格权重、相似度计算、中文转换 |
| TestBrandAPI | 3 | 品牌 API 端点 |
| TestCategoryAPI | 3 | 分类 API 端点 |
| TestEquipmentAPI | 5 | 装备 API 端点 |
| TestProfileAPI | 3 | 用户档案 API 端点 |
| TestReviewAPI | 3 | 评价 API 端点 |
| TestRecommendationAPI | 5 | 推荐 API 端点 |
| TestHealthCheck | 2 | 健康检查端点 |

## 测试分类

### Unit Tests（单元测试）

标记: `@pytest.mark.unit`

- 测试单个函数或类的独立功能
- 使用 Mock 隔离外部依赖
- 执行速度快，适合频繁运行

```python
class TestBrandSchemas:
    def test_brand_create_valid(self):
        """测试创建品牌 Schema - 有效数据"""
        data = BrandCreate(name="Butterfly", display_name="蝴蝶")
        assert data.name == "Butterfly"
```

### Integration Tests（集成测试）

标记: `@pytest.mark.integration`

- 测试多个模块之间的交互
- 使用真实数据库（内存 SQLite）
- 验证跨模块数据流

```python
@pytest.mark.integration
class TestLLMAndLearningResources:
    def test_search_learning_resources_with_llm(self, client):
        """测试通过 LLM 语义搜索学习资源"""
        response = client.post("/api/learning/resources/search", json={...})
```

### E2E Tests（端到端测试）

标记: `@pytest.mark.e2e`

- 测试完整的用户流程
- 模拟真实使用场景
- 验证系统整体行为

```python
@pytest.mark.e2e
class TestUserRegistrationFlow:
    def test_complete_user_registration_flow(self, client):
        """测试完整的用户注册流程"""
        # 1. 创建用户档案
        # 2. 检查档案完整度
        # 3. 获取个性化推荐
```

## pytest 配置说明

### pytest.ini

```ini
[pytest]
testpaths = tests
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

markers =
    unit: 单元测试 - 测试单个函数或类的独立功能
    integration: 集成测试 - 测试多个模块之间的交互
    e2e: 端到端测试 - 测试完整的用户流程
    slow: 慢速测试 - 执行时间较长的测试，可选跳过

filterwarnings =
    ignore::DeprecationWarning:pydantic.*
    ignore::PendingDeprecationWarning
    ignore::pytest.PytestUnraisableExceptionWarning

addopts = -v --tb=short
```

### conftest.py Fixtures

| Fixture | 作用域 | 说明 |
|---------|--------|------|
| `async_db_session` | function | 异步测试数据库会话（SQLite 内存） |
| `mock_db_session` | function | 模拟数据库会话（用于单元测试） |
| `client` | function | FastAPI TestClient（不抛出异常） |
| `client_with_exceptions` | function | FastAPI TestClient（抛出异常，用于调试） |
| `temp_dir` | function | 临时目录 |
| `temp_file` | function | 临时文件 |
| `data_factory` | function | 测试数据工厂（生成 Schema 数据） |
| `orm_factory` | function | ORM 模型工厂（生成数据库记录） |
| `mock_embedding_service` | function | 模拟 Embedding 服务 |
| `mock_openai_client` | function | 模拟 OpenAI 客户端 |
| `reset_singletons` | function (autouse) | 每个测试后重置服务单例 |

### DataFactory 方法

```python
DataFactory.brand_data(name="TestBrand")      # 品牌数据
DataFactory.category_data(name="blade")       # 分类数据
DataFactory.equipment_data(brand_id, cat_id)  # 装备数据
DataFactory.user_profile_data(user_id)        # 用户档案数据
DataFactory.review_data(equipment_id)         # 评价数据
DataFactory.recommendation_request_data()      # 推荐请求数据
DataFactory.search_request_data()              # 搜索请求数据
```

### ORMFactory 方法

```python
ORMFactory.create_brand()           # 创建 Brand ORM 模型
ORMFactory.create_category()        # 创建 EquipmentCategory ORM 模型
ORMFactory.create_equipment()       # 创建 Equipment ORM 模型
ORMFactory.create_user_profile()    # 创建 UserEquipmentProfile ORM 模型
ORMFactory.create_review()          # 创建 EquipmentReview ORM 模型
```

## Pydantic 警告修复记录

### 问题描述

Pydantic V2 弃用了 `class Config` 内部类语法，需要迁移到 `model_config = ConfigDict(...)` 格式。

### 迁移前后对比

```python
# 迁移前（已弃用）
class MyModel(BaseModel):
    name: str

    class Config:
        from_attributes = True

# 迁移后
from pydantic import ConfigDict

class MyModel(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)
```

### 修复文件清单

| 文件 | 修改处数 | 说明 |
|------|----------|------|
| `app/social_media/schemas.py` | 7 | 社交媒体响应模型 |
| `app/training_analysis/schemas.py` | 8 | 训练分析响应模型 |
| `app/equipment_recommendation/schemas.py` | 8 | 装备推荐响应模型 |
| `app/ball_tracking/schemas.py` | 6 | 球追踪响应模型 |
| `app/learning_resources/schemas.py` | 14 | 学习资源响应模型 |
| `app/llm/schemas.py` | 4 | LLM 响应模型 |
| `config/settings.py` | 1 | Settings 配置类 |
| **总计** | **48** | |

### Settings 特殊处理

`pydantic-settings` 使用 `SettingsConfigDict`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    llm_api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
```

## 运行命令参考

### 全量测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行所有测试（简洁输出）
pytest tests/

# 运行所有测试（显示详细错误）
pytest tests/ -v --tb=long
```

### 模块测试

```bash
# 运行装备模块测试
pytest tests/test_equipment.py -v

# 运行 LLM 模块测试
pytest tests/test_llm.py -v

# 运行多个模块
pytest tests/test_equipment.py tests/test_llm.py -v
```

### 按标记运行

```bash
# 运行单元测试
pytest -m "unit" -v

# 运行集成测试
pytest -m "integration" -v

# 运行端到端测试
pytest -m "e2e" -v

# 排除慢速测试
pytest -m "not slow" -v
```

### 覆盖率测试

```bash
# 生成覆盖率报告（终端）
pytest --cov=app --cov-report=term

# 生成 HTML 覆盖率报告
pytest --cov=app --cov-report=html

# 指定最低覆盖率
pytest --cov=app --cov-fail-under=80
```

### 其他常用选项

```bash
# 失败后立即停止
pytest tests/ -x

# 只运行上次失败的测试
pytest tests/ --lf

# 显示最慢的 10 个测试
pytest tests/ --durations=10

# 并行运行（需要 pytest-xdist）
pytest tests/ -n auto
```

## Skipped 测试说明

当前有 2 个测试被跳过，原因如下：

### 1. GPU 相关测试

位于 `test_ball_tracking.py`，在没有 GPU 的环境下会自动跳过：

```python
@pytest.mark.skipif(not torch.cuda.is_available(), reason="需要 GPU")
def test_blurball_inference():
    """测试 BlurBall 模型推理"""
    pass
```

### 2. 外部服务依赖测试

某些测试依赖外部服务（如 OpenAI API），在 CI 环境中会跳过：

```python
@pytest.mark.skipif(os.getenv("CI") == "true", reason="CI 环境跳过")
def test_llm_real_completion():
    """测试真实 LLM 调用"""
    pass
```

## Warnings 说明

当前有 3 个警告，均为第三方库产生的 DeprecationWarning：

### 1-3. FAISS SWIG 警告

```
DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute
DeprecationWarning: builtin type SwigPyObject has no __module__ attribute
DeprecationWarning: builtin type swigvarlink has no __module__ attribute
```

**来源**: FAISS 库的 SWIG 绑定
**影响**: 无功能影响，仅在导入时产生警告
**处理**: 已在 `pytest.ini` 中配置忽略

这些警告来自 FAISS 向量库使用的 SWIG (Simplified Wrapper and Interface Generator) 绑定。这是 FAISS 的实现细节，不影响测试结果或应用功能。

## 测试最佳实践

### 1. 测试命名规范

```python
def test_<功能>_<场景>_<预期结果>():
    """中文描述"""
    pass

# 示例
def test_brand_create_valid(self):
    """测试创建品牌 Schema - 有效数据"""

def test_brand_create_empty_name(self):
    """测试创建品牌 Schema - 空名称应失败"""
```

### 2. 测试类组织

```python
class TestBrandSchemas:        # Schema 验证
class TestBrandService:        # 服务层逻辑
class TestBrandAPI:            # API 端点
```

### 3. Mock 使用

```python
from unittest.mock import patch, MagicMock, AsyncMock

# 同步函数 Mock
with patch("module.function") as mock:
    mock.return_value = expected_value

# 异步函数 Mock
with patch("module.async_function", new_callable=AsyncMock) as mock:
    mock.return_value = expected_value
```

### 4. 异步测试

```python
@pytest.mark.asyncio
async def test_async_operation(self, async_db_session):
    result = await service.create_item(async_db_session, data)
    assert result is not None
```

## 持续集成建议

### GitHub Actions 配置示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

*文档版本: 1.0*
*更新日期: 2026-02-19*
*测试框架: pytest 9.0.2 + pytest-asyncio 0.24.0*
