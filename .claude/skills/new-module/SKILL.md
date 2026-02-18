# new-module

创建新的业务模块，遵循项目标准结构。

## 使用方式

```
/new-module <module_name>
```

## 执行步骤

1. 在 `app/` 下创建模块目录结构：
   ```
   app/<module_name>/
   ├── __init__.py          # 模块说明注释
   ├── core/
   │   └── __init__.py      # 核心业务逻辑
   └── api/
       └── __init__.py      # FastAPI router + /health 端点
   ```

2. `api/__init__.py` 模板：
   ```python
   from fastapi import APIRouter

   router = APIRouter()

   @router.get("/health")
   async def health_check():
       """<module_name> 模块健康检查"""
       return {"module": "<module_name>", "status": "healthy"}
   ```

3. 在 `app/main.py` 中注册 router：
   ```python
   from app.<module_name>.api import router as <module_name>_router
   app.include_router(<module_name>_router, prefix="/api/<module-name>", tags=["<ModuleName>"])
   ```

4. 运行 `ruff check .` 确保代码风格正确

5. 启动服务测试 `/api/<module-name>/health` 端点

## 命名规范

- 目录名：snake_case（如 `user_profile`）
- URL 前缀：kebab-case（如 `/api/user-profile`）
- Router 变量：snake_case + `_router` 后缀
