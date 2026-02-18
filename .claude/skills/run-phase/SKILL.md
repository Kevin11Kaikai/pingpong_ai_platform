# run-phase

按阶段编号加载开发计划，进入 Plan Mode 引导开发。

## 使用方式

```
/run-phase <phase_number>
```

## 开发阶段

| Phase | 名称 | 说明 |
|-------|------|------|
| 1 | 基础架构 | 项目结构、配置、Docker（已完成） |
| 2 | LLM/RAG | OpenAI API 集成、RAG 检索、对话管理 |
| 3 | Ball Tracking | BlurBall + TT3D 集成、视频处理、轨迹分析 |
| 4 | Equipment | 装备数据库、推荐算法、用户偏好 |
| 5 | Social Media | 平台问答抓取、内容分析、自动回复 |
| 6 | Learning Resources | 教程索引、视频分析、学习路径 |
| 7 | Training Analysis | 训练数据采集、统计分析、进度追踪 |
| 8 | Frontend | Web UI、可视化、用户交互 |
| 9 | 测试 | 单元测试、集成测试、E2E 测试 |
| 10 | 部署 | Docker 优化、CI/CD、监控 |

## 执行步骤

1. 确认当前 Phase 编号

2. 进入 Plan Mode，执行以下分析：
   - 阅读 CLAUDE.md 了解项目约定
   - 检查该 Phase 相关模块的现有代码
   - 列出该 Phase 的具体任务清单
   - 识别依赖项和前置条件

3. 输出开发计划：
   - 需要创建/修改的文件列表
   - 需要安装的依赖
   - 关键实现步骤
   - 验证方式

4. 等待用户确认后开始执行

## 示例

```
/run-phase 2
```

将进入 Plan Mode，规划 LLM/RAG 模块的开发：
- OpenAI client 封装
- RAG 检索实现
- 对话历史管理
- API endpoints

## 注意事项

- 每个 Phase 完成后提交代码
- 遵循 CLAUDE.md 中的编码规范
- 显存敏感操作参考显存管理规则
- 使用 `/commit` 提交符合规范的 commit
