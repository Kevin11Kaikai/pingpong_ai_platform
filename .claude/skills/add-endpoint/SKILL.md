# add-endpoint

为现有模块添加 FastAPI endpoint。

## 使用方式

```
/add-endpoint <module_name> <endpoint_name> [method]
```

- `module_name`: 目标模块（如 llm, ball_tracking）
- `endpoint_name`: 端点名称（如 chat, analyze）
- `method`: HTTP 方法，默认 POST

## 执行步骤

1. 在 `app/<module_name>/core/` 中创建业务逻辑：
   - 函数名用英文，注释用中文
   - 必须添加 type hints

2. 在 `app/<module_name>/api/` 中创建 Pydantic 模型：
   ```python
   from pydantic import BaseModel, Field

   class <Endpoint>Request(BaseModel):
       """请求模型"""
       field: str = Field(..., description="字段说明")

   class <Endpoint>Response(BaseModel):
       """响应模型"""
       success: bool
       data: dict | None = None
       message: str | None = None
   ```

3. 添加 endpoint 到 router：
   ```python
   from fastapi import APIRouter, HTTPException, status

   @router.<method>("/<endpoint_name>")
   async def <endpoint_name>(request: <Endpoint>Request) -> <Endpoint>Response:
       """
       <端点中文说明>

       - 参数说明
       - 返回说明
       """
       try:
           # 调用 core 层逻辑
           result = await core_function(request)
           return <Endpoint>Response(success=True, data=result)
       except ValueError as e:
           raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
       except Exception as e:
           raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="内部错误")
   ```

4. 在 `tests/` 中添加测试：
   ```python
   import pytest
   from httpx import AsyncClient, ASGITransport
   from app.main import app

   @pytest.mark.asyncio
   async def test_<endpoint_name>():
       async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
           response = await client.<method>("/api/<module-name>/<endpoint_name>", json={...})
           assert response.status_code == 200
   ```

5. 运行 `ruff check .` 和 `pytest tests/ -v -k "<endpoint_name>"`

## 错误处理规范

- 400: 请求参数错误
- 401: 未认证
- 403: 无权限
- 404: 资源不存在
- 500: 内部错误
