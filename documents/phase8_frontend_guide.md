# Phase 8: Frontend 开发指南

## 概述

使用原生 HTML + CSS + JavaScript 构建乒乓球 AI 平台的 Web 前端界面，覆盖全部 6 个功能模块。

## 技术栈

| 技术 | 用途 |
|------|------|
| HTML5 | 页面结构 |
| CSS3 (Grid/Flexbox) | 响应式布局 |
| Vanilla JavaScript (ES6+) | 交互逻辑 |
| Chart.js | 数据可视化 |
| HTML5 Video + Canvas | 视频播放、轨迹叠加 |
| EventSource/Fetch | API 调用 |

## 目录结构

```
frontend/
├── index.html                    # 入口页面（仪表盘）
├── pages/
│   ├── chat.html                 # LLM 聊天界面
│   ├── video.html                # 视频分析界面
│   ├── equipment.html            # 装备推荐界面
│   ├── learning.html             # 学习资源界面
│   ├── training.html             # 训练分析界面
│   └── social.html               # 社交媒体界面
├── css/
│   ├── base.css                  # 基础样式、CSS 变量
│   ├── layout.css                # 布局样式
│   ├── components.css            # 组件样式
│   └── pages.css                 # 页面特定样式
├── js/
│   ├── api/
│   │   ├── client.js             # API 基础客户端
│   │   ├── llm.js                # LLM 模块 API
│   │   ├── ball-tracking.js      # 视频分析 API
│   │   ├── equipment.js          # 装备推荐 API
│   │   ├── learning.js           # 学习资源 API
│   │   ├── training.js           # 训练分析 API
│   │   └── social.js             # 社交媒体 API
│   ├── components/
│   │   ├── nav.js                # 导航组件
│   │   ├── toast.js              # 消息提示
│   │   ├── modal.js              # 弹窗组件
│   │   ├── loading.js            # 加载状态
│   │   └── pagination.js         # 分页组件
│   ├── pages/
│   │   ├── dashboard.js          # 仪表盘页面逻辑
│   │   ├── chat.js               # 聊天页面逻辑
│   │   ├── video.js              # 视频页面逻辑
│   │   ├── equipment.js          # 装备页面逻辑
│   │   ├── learning.js           # 学习页面逻辑
│   │   ├── training.js           # 训练页面逻辑
│   │   └── social.js             # 社交页面逻辑
│   ├── utils/
│   │   ├── format.js             # 格式化工具
│   │   ├── storage.js            # 本地存储
│   │   └── canvas.js             # Canvas 工具
│   └── main.js                   # 主入口
├── assets/
│   ├── icons/                    # SVG 图标
│   └── images/                   # 图片资源
└── lib/
    └── chart.min.js              # Chart.js 备份
```

## 页面功能

### 1. 仪表盘 (index.html)
- 系统健康状态卡片
- 快速入口按钮
- 最近活动列表
- 统计概览

### 2. LLM 聊天 (chat.html)
- 对话列表侧边栏
- 实时流式消息 (SSE)
- Markdown 渲染
- 知识库文档管理

### 3. 视频分析 (video.html)
- 视频拖拽上传
- 任务状态追踪
- Canvas 轨迹叠加
- 分析结果展示

### 4. 装备推荐 (equipment.html)
- 装备搜索/筛选
- 分类浏览
- 对比功能
- 个性化推荐

### 5. 学习资源 (learning.html)
- 资源浏览/搜索
- 学习路径展示
- Chart.js 进度图
- 书签管理

### 6. 训练分析 (training.html)
- 训练会话列表
- 训练数据录入
- Chart.js 趋势图
- AI 训练建议

### 7. 社交媒体 (social.html)
- 内容搜索/筛选
- AI 内容分析
- 回复生成
- 抓取任务管理

## 后端集成

### 静态文件服务

已在 `app/main.py` 中配置：

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 挂载静态文件
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# SPA 入口
@app.get("/")
async def serve_index():
    return FileResponse("frontend/index.html")
```

### CORS 配置

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## UI 设计规范

### 颜色方案

```css
:root {
  --primary: #1890ff;      /* 主色 */
  --success: #52c41a;      /* 成功 */
  --warning: #faad14;      /* 警告 */
  --error: #ff4d4f;        /* 错误 */
  --text: #333333;         /* 主文字 */
  --text-secondary: #666;  /* 次要文字 */
  --border: #d9d9d9;       /* 边框 */
  --bg: #f5f5f5;           /* 背景 */
  --card-bg: #ffffff;      /* 卡片背景 */
}
```

### 布局
- 侧边栏导航 (固定 240px)
- 主内容区 (自适应)
- 响应式断点: 768px, 1024px

### 组件风格
- 圆角: 8px
- 阴影: `0 2px 8px rgba(0,0,0,0.1)`
- 间距: 8px 基础单位

## CDN 依赖

```html
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

<!-- Marked.js (Markdown 渲染) -->
<script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
```

## 启动和访问

1. 启动后端服务：
```bash
conda activate pingpong_ai
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. 访问前端：
```
http://localhost:8000/
```

3. 页面导航：
- 仪表盘: `/`
- AI 聊天: `/chat`
- 视频分析: `/video`
- 装备推荐: `/equipment`
- 学习资源: `/learning`
- 训练分析: `/training`
- 社交媒体: `/social`

## 验证方式

1. 访问首页，检查仪表盘显示
2. 点击侧边栏导航，验证各页面加载
3. 测试功能：
   - 聊天页面：发送消息测试
   - 视频页面：上传视频测试
   - 装备页面：搜索和筛选测试
   - 学习页面：浏览资源测试
   - 训练页面：创建会话测试
   - 社交页面：搜索内容测试
4. 响应式测试：调整浏览器窗口大小
5. 控制台检查：无 JavaScript 错误

## 注意事项

1. 所有 API 调用使用相对路径 `/api/*`
2. 本地存储使用 `pingpong_` 前缀
3. 流式聊天使用 POST + ReadableStream 模式
4. Canvas 叠加层需要视频元素先加载完成
5. Chart.js 图表需要在 DOM 完全加载后初始化
