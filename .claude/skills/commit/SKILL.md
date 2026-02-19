# commit

使用 Conventional Commits 规范提交代码。

---
disable-model-invocation: true
---

## 使用方式

```
/commit [message]
```

## Commit 格式

```
<type>(<scope>): <description>
```

### Type（必选）

| Type | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| style | 代码格式（不影响功能） |
| refactor | 重构（不新增功能、不修复 bug） |
| perf | 性能优化 |
| test | 测试相关 |
| chore | 构建/工具/依赖更新 |

### Scope（必选，使用模块名）

| Scope | 说明 |
|-------|------|
| infra | 基础架构、配置、Docker |
| llm | LLM 学习助手模块 |
| ball-tracking | 球体追踪模块 |
| equipment | 装备推荐模块 |
| social-media | 社交媒体问答模块 |
| learning | 学习资源模块 |
| training | 训练分析模块 |
| shared | 共享工具 |
| deps | 依赖管理 |

### Description

- 使用英文，首字母小写
- 不加句号
- 简洁描述变更内容

## 示例

```bash
git add .
git commit -m "feat(llm): add chat completion endpoint"
git commit -m "fix(ball-tracking): resolve frame drop issue"
git commit -m "chore(deps): upgrade fastapi to 0.115.0"
git commit -m "refactor(shared): simplify gpu manager context"
```

## 提交前检查

1. `ruff check .` — 代码风格
2. `pytest tests/ -v` — 单元测试
3. `git status` — 确认变更文件
4. `git diff --staged` — 检查暂存内容
