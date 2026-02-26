# Ball Tracking 模块技术文档

> 本文档详细介绍 BlurBall 算法原理、模块架构和测试流程

---

## 目录

1. [BlurBall 算法原理](#1-blurball-算法原理)
2. [模块架构设计](#2-模块架构设计)
3. [数据流与处理流程](#3-数据流与处理流程)
4. [测试方案](#4-测试方案)
5. [使用指南](#5-使用指南)
6. [常见问题](#6-常见问题)

---

## 1. BlurBall 算法原理

### 1.1 背景与动机

乒乓球是世界上速度最快的球类运动之一，球速可达 **150 km/h**。在标准 30fps 视频中，高速运动的球会产生明显的 **运动模糊 (Motion Blur)**，这给传统目标检测算法带来了巨大挑战：

| 挑战 | 说明 |
|------|------|
| 运动模糊 | 球呈现为拉长的条纹而非圆形 |
| 小目标 | 乒乓球直径仅 40mm，在画面中占比极小 |
| 高速运动 | 帧间位移大，传统追踪易丢失 |
| 遮挡 | 球拍、球网、人体遮挡频繁 |

### 1.2 BlurBall 核心创新

**BlurBall** 是 2025 年发表的最新乒乓球检测算法，由德国图宾根大学提出。

**论文**: *BlurBall: Joint Ball and Motion Blur Estimation for Table Tennis Ball Tracking*
**arXiv**: https://arxiv.org/abs/2509.18387

#### 核心创新点

```
┌─────────────────────────────────────────────────────────────┐
│                    BlurBall 关键创新                         │
├─────────────────────────────────────────────────────────────┤
│ 1. 多帧感知 (Multi-frame MIMO)                              │
│    • 输入: 3 帧连续图像                                      │
│    • 输出: 3 帧对应的热力图                                  │
│    • 优势: 利用时序信息理解运动方向                          │
├─────────────────────────────────────────────────────────────┤
│ 2. 联合模糊估计                                             │
│    • 不仅检测球位置 (x, y)                                   │
│    • 同时预测模糊长度 (length) 和角度 (angle)                │
│    • 优势: 提供运动方向和速度信息                            │
├─────────────────────────────────────────────────────────────┤
│ 3. 线性热力图标注                                           │
│    • 传统方法: 高斯点热力图                                  │
│    • BlurBall: 沿模糊方向的高斯线热力图                      │
│    • 优势: 更好地匹配模糊球的形态                            │
├─────────────────────────────────────────────────────────────┤
│ 4. 模糊中心标注规范                                          │
│    • 传统: 标注在模糊起点                                    │
│    • BlurBall: 标注在模糊中心                                │
│    • 优势: 提高位置预测准确性                                │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 网络架构

BlurBall 基于 **HRNet-W48** (High-Resolution Network) 骨干网络，并加入 **SE (Squeeze-and-Excitation)** 注意力机制。

```
输入图像 (3帧 × 3通道 = 9通道)
    │
    ▼
┌─────────────────────────────────────────────┐
│                  Stem                        │
│   Conv1: 64通道, 3×3, stride=1              │
│   Conv2: 64通道, 3×3, stride=1              │
│   (无下采样，保持分辨率 288×512)             │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│               Stage 1                        │
│   1 个 Bottleneck 块                         │
│   通道数: [32]                               │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│               Stage 2                        │
│   2 个并行分支 (多尺度)                      │
│   通道数: [16, 32]                           │
│   BasicBlock + SE 注意力                     │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│               Stage 3                        │
│   3 个并行分支                               │
│   通道数: [16, 32, 64]                       │
│   多尺度特征融合                             │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│               Stage 4                        │
│   4 个并行分支                               │
│   通道数: [16, 32, 64, 128]                  │
│   最高级多尺度特征                           │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│             Final Conv                       │
│   1×1 卷积 → 3通道输出                       │
│   输出: 3帧热力图 (3, 288, 512)              │
└─────────────────────────────────────────────┘
```

#### SE (Squeeze-and-Excitation) 注意力机制

```python
# SE Block 伪代码
def se_block(x, reduction=16):
    # Squeeze: 全局平均池化
    z = global_avg_pool(x)  # [C, H, W] → [C, 1, 1]

    # Excitation: 两个全连接层
    s = fc1(z, C // reduction)  # 压缩
    s = relu(s)
    s = fc2(s, C)               # 扩展
    s = sigmoid(s)              # 归一化到 [0, 1]

    # Scale: 通道加权
    return x * s
```

**作用**: 自适应地为每个通道分配权重，增强重要特征，抑制无关特征。

### 1.4 后处理流程

模型输出热力图后，需要通过后处理提取球的位置和模糊参数。

```
热力图 (288 × 512)
    │
    ▼
┌─────────────────────────────────────────────┐
│           1. 阈值化                          │
│   mask = heatmap > threshold (0.5)          │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│           2. 连通分量分析                    │
│   cv2.connectedComponentsWithStats()        │
│   找出所有连通区域                           │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│           3. 加权质心计算                    │
│   使用热力图值作为权重                       │
│   center = Σ(pos × weight) / Σ(weight)      │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│           4. PCA 主轴分析                    │
│   cv2.PCACompute()                          │
│   计算模糊方向（第一主成分）                 │
│   angle = arctan2(eigenvector)              │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│           5. 模糊长度计算                    │
│   沿主轴方向测量连通分量的长度               │
│   length = 连通区域沿主轴的跨度              │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│           6. 仿射逆变换                      │
│   将检测坐标从 288×512 变换回原图坐标        │
│   (x', y') = inverse_affine(x, y)           │
└─────────────────────────────────────────────┘
    │
    ▼
输出: {x, y, angle, length, confidence}
```

### 1.5 在线追踪器

BlurBall 使用简单但有效的在线追踪策略：

```python
class OnlineBlurTracker:
    def __init__(self, max_disp=150):
        self.max_disp = max_disp  # 最大帧间位移
        self.last_pos = None
        self.lost_count = 0

    def update(self, detections):
        if not detections:
            self.lost_count += 1
            return {"visi": False, "x": self.last_pos[0], "y": self.last_pos[1]}

        # 选择最接近上一帧位置的检测
        best = min(detections, key=lambda d: distance(d, self.last_pos))

        if distance(best, self.last_pos) < self.max_disp:
            self.last_pos = (best.x, best.y)
            self.lost_count = 0
            return {"visi": True, "x": best.x, "y": best.y,
                    "angle": best.angle, "length": best.length,
                    "score": best.score}
        else:
            self.lost_count += 1
            return {"visi": False, ...}
```

---

## 2. 模块架构设计

### 2.1 整体架构

```
app/ball_tracking/
├── __init__.py              # 模块导出
├── models.py                # SQLAlchemy 数据库模型
├── schemas.py               # Pydantic 数据结构
├── core/                    # 核心业务逻辑
│   ├── detector.py          # BlurBall 检测器封装
│   ├── tracker.py           # 多帧追踪器
│   ├── trajectory_analyzer.py  # 轨迹分析
│   ├── video_processor.py   # 视频处理
│   ├── visualizer.py        # 可视化
│   └── pipeline.py          # 主处理流程
└── api/                     # REST API
    ├── videos.py            # 视频上传/处理
    ├── trajectories.py      # 轨迹查询
    ├── analysis.py          # 分析结果
    └── visualization.py     # 可视化输出
```

### 2.2 核心组件

#### 2.2.1 BlurBallDetector

封装 BlurBall 模型的检测器。

```python
class BlurBallDetector:
    """BlurBall 检测器"""

    def __init__(self, checkpoint_path, score_threshold=0.5, device="cuda"):
        self.checkpoint_path = checkpoint_path
        self.score_threshold = score_threshold
        self.device = device

    def load_model(self):
        """加载模型到 GPU"""
        # 构建配置
        # 导入 BlurBall 模块
        # 加载权重

    def detect_frames(self, frames, frame_indices) -> List[BallDetection]:
        """批量检测多帧"""
        # 预处理 → 模型推理 → 后处理

    def unload_model(self):
        """卸载模型，释放显存"""
```

#### 2.2.2 BallTracker

跨帧追踪和轨迹关联。

```python
class BallTracker:
    """多帧追踪器"""

    def __init__(self, max_gap_frames=5, max_distance=150, min_track_length=3):
        self.max_gap_frames = max_gap_frames  # 最大允许丢失帧数
        self.max_distance = max_distance       # 最大帧间位移
        self.min_track_length = min_track_length  # 最小轨迹长度

    def process_detections(self, detections, fps) -> List[BallTrack]:
        """处理检测序列，生成轨迹"""
        # 遍历检测结果
        # 关联到现有轨迹或创建新轨迹
        # 插值填充缺失帧

    def smooth_track(self, track, window_size=3) -> BallTrack:
        """平滑轨迹"""
        # 滑动窗口均值滤波
```

#### 2.2.3 TrajectoryAnalyzer

从轨迹提取物理特性。

```python
class TrajectoryAnalyzer:
    """轨迹分析器"""

    def __init__(self, pixels_per_meter=500):
        self.pixels_per_meter = pixels_per_meter

    def analyze_track(self, track) -> AnalysisResult:
        """分析单条轨迹"""
        speed_stats = self._compute_speed_stats(track)
        motion_stats = self._compute_motion_stats(track)
        bounce_points = self._detect_bounces(track)
        stroke_type = self._classify_stroke(track, speed_stats)
        return AnalysisResult(...)

    def _classify_stroke(self, track, speed_stats) -> str:
        """分类击球类型: push/chop/loop/drive/smash"""
```

#### 2.2.4 BallTrackingPipeline

协调完整处理流程。

```python
class BallTrackingPipeline:
    """主处理 Pipeline"""

    async def process_video(self, video_path, progress_callback):
        """处理视频文件"""
        # 1. 读取视频元数据 (10%)
        # 2. BlurBall 检测 (10-70%)
        # 3. 多帧追踪 (70-85%)
        # 4. 轨迹分析 (85-100%)
        return PipelineResult(...)
```

### 2.3 数据结构

```python
@dataclass
class BallDetection:
    """单帧检测结果"""
    frame_idx: int
    x: float                    # 中心 x 坐标
    y: float                    # 中心 y 坐标
    confidence: float           # 检测置信度
    blur_angle: Optional[float] # 模糊角度（度）
    blur_length: Optional[float]# 模糊长度（像素）
    visible: bool

@dataclass
class TrackPoint:
    """轨迹点"""
    frame_idx: int
    timestamp_ms: float
    x: float
    y: float
    confidence: float
    blur_angle: Optional[float]
    blur_length: Optional[float]
    interpolated: bool          # 是否为插值点

@dataclass
class BallTrack:
    """完整轨迹"""
    track_id: str
    points: List[TrackPoint]

    @property
    def duration_ms(self) -> float
    @property
    def point_count(self) -> int

@dataclass
class AnalysisResult:
    """分析结果"""
    track_id: str
    speed_stats: SpeedStats      # 速度统计
    motion_stats: MotionStats    # 运动统计
    bounce_points: List[BouncePoint]  # 落点
    stroke_type: str             # 击球类型
```

---

## 3. 数据流与处理流程

### 3.1 完整处理流程

```
                              Ball Tracking 处理流程
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   输入视频                                                               │
│      │                                                                   │
│      ▼                                                                   │
│   ┌──────────────────┐                                                   │
│   │  VideoProcessor  │  读取视频元数据                                   │
│   │  提取视频帧      │  width, height, fps, total_frames                 │
│   └────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌──────────────────┐                                                   │
│   │ BlurBallDetector │  GPU 推理                                         │
│   │   批量检测       │  输入: List[BGR帧]                                │
│   │                  │  输出: List[BallDetection]                        │
│   └────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌──────────────────┐                                                   │
│   │   BallTracker    │  CPU 处理                                         │
│   │   轨迹关联       │  • 跨帧关联检测结果                               │
│   │   间隙插值       │  • 处理遮挡和丢失                                 │
│   │   轨迹平滑       │  • 生成连续轨迹                                   │
│   └────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌──────────────────┐                                                   │
│   │TrajectoryAnalyzer│  CPU 处理                                         │
│   │   速度分析       │  • 计算速度统计                                   │
│   │   运动分析       │  • 检测落点                                       │
│   │   击球分类       │  • 分类击球类型                                   │
│   └────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌──────────────────┐                                                   │
│   │    存储结果      │                                                   │
│   │  数据库/文件     │                                                   │
│   └────────┬─────────┘                                                   │
│            │                                                             │
│            ▼                                                             │
│   ┌──────────────────┐                                                   │
│   │TrajectoryVisualizer│ (可选)                                          │
│   │   生成可视化视频  │                                                  │
│   └──────────────────┘                                                   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 显存管理

由于 RTX 4080 Super 显存为 16GB，需要合理管理 CV 模型的加载：

```python
# 使用 GPUManager 管理模型生命周期
with GPUManager.load_model("BlurBall"):
    detector = get_detector()
    detector.load_model()

    try:
        # 批量处理
        for batch in video_processor.extract_frames_batch(batch_size=16):
            detections = detector.detect_frames(batch)
    finally:
        detector.unload_model()  # 显式释放

# 自动调用 torch.cuda.empty_cache()
```

**显存占用估算**:

| 组件 | 显存占用 |
|------|----------|
| BlurBall (HRNet-W48) | ~2-3 GB |
| 批处理 (batch_size=16) | ~1-2 GB |
| 预留 | ~2 GB |
| **总计** | **~5-7 GB** |

---

## 4. 测试方案

### 4.1 测试架构

```
tests/
├── test_ball_tracking.py     # 完整测试套件
│   ├── TestBallDetection     # 数据结构测试
│   ├── TestBallTracker       # 追踪器测试
│   ├── TestTrajectoryAnalyzer # 分析器测试
│   ├── TestVideoProcessor    # 视频处理测试
│   ├── TestBallTrackingPipeline # Pipeline 测试
│   ├── TestPerformance       # 性能测试
│   ├── TestValidation        # 有效性验证
│   └── TestEndToEnd          # 端到端测试 (需要真实视频)
│
scripts/
└── verify_ball_tracking.py   # 快速验证脚本
```

### 4.2 单元测试

#### 4.2.1 追踪器测试

```python
class TestBallTracker:
    def test_process_linear_trajectory(self):
        """测试线性轨迹处理"""
        # 创建 10 帧连续检测
        # 验证生成 1 条轨迹
        # 验证轨迹点数 = 10

    def test_process_trajectory_with_gaps(self):
        """测试带间隙的轨迹"""
        # 创建 15 帧，帧 5-6 缺失
        # 验证仍生成 1 条轨迹（插值填充）
        # 验证插值点数 = 2

    def test_process_multiple_tracks(self):
        """测试多轨迹分割"""
        # 创建位置跳跃的检测序列
        # 验证分割为 2 条轨迹

    def test_smooth_track(self):
        """测试轨迹平滑"""
        # 创建带噪声的轨迹
        # 验证平滑后点数不变
```

#### 4.2.2 分析器测试

```python
class TestTrajectoryAnalyzer:
    def test_speed_stats(self):
        """测试速度统计"""
        # 创建匀速轨迹
        # 验证速度计算正确

    def test_bounce_detection(self):
        """测试落点检测"""
        # 创建抛物线轨迹
        # 验证检测到落点

    def test_stroke_classification(self):
        """测试击球分类"""
        # 快速轨迹 → drive/smash
        # 慢速轨迹 → push/chop
```

### 4.3 有效性验证

```python
class TestValidation:
    def test_track_continuity(self):
        """验证轨迹连续性"""
        # 帧索引递增
        # 时间戳递增

    def test_speed_reasonability(self):
        """验证速度合理性"""
        # 乒乓球速度 < 200 km/h
        # 正常比赛 20-100 km/h

    def test_position_bounds(self):
        """验证位置边界"""
        # 坐标在视频分辨率范围内
```

### 4.4 端到端测试

```python
async def run_e2e_test(video_path: str):
    """端到端测试"""
    # 1. 测试视频处理器
    with VideoProcessor(video_path) as processor:
        metadata = processor.get_metadata()
        assert metadata.total_frames > 0

    # 2. 测试检测器（需要模型）
    detector = get_detector()
    detector.load_model()
    detections = detector.detect_frames(sample_frames)
    detector.unload_model()

    # 3. 测试完整 Pipeline
    pipeline = get_pipeline()
    result = await pipeline.process_video(video_path)

    # 验证结果
    assert result.tracks is not None
    assert len(result.tracks) >= 0
    assert result.processing_time_seconds > 0
```

### 4.5 运行测试

```bash
# 运行所有单元测试（不需要 GPU/模型）
pytest tests/test_ball_tracking.py -v -m "not e2e"

# 运行特定测试类
pytest tests/test_ball_tracking.py::TestBallTracker -v

# 运行端到端测试（需要视频和模型）
TEST_VIDEO_PATH=path/to/video.mp4 pytest tests/test_ball_tracking.py -v -m e2e

# 快速验证
python scripts/verify_ball_tracking.py

# 带视频的完整验证
python scripts/verify_ball_tracking.py --video path/to/video.mp4 --visualize
```

---

## 5. 使用指南

### 5.1 环境准备

```bash
# 激活 conda 环境
conda activate pingpong_ai

# 确保 BlurBall 模型已下载
# 模型应放置在: external/blurball/checkpoints/blurball_best
```

### 5.2 API 使用

#### 上传视频并处理

```bash
# 上传视频
curl -X POST "http://localhost:8000/api/ball-tracking/upload" \
  -F "file=@video.mp4"

# 返回: {"job_id": "xxx", "status": "queued"}
```

#### 查询处理状态

```bash
curl "http://localhost:8000/api/ball-tracking/jobs/{job_id}/status"

# 返回: {"status": "processing", "progress_percent": 45, "current_stage": "detecting"}
```

#### 获取结果

```bash
curl "http://localhost:8000/api/ball-tracking/jobs/{job_id}/result"

# 返回完整处理结果，包含轨迹和分析
```

### 5.3 代码调用

```python
import asyncio
from app.ball_tracking.core.pipeline import get_pipeline, PipelineConfig

async def process_video(video_path: str):
    config = PipelineConfig(
        enable_trajectory_analysis=True,
        batch_size=16,
        detection_threshold=0.5,
    )
    pipeline = get_pipeline(config)

    async def progress_callback(stage, progress):
        print(f"{stage}: {progress}%")

    result = await pipeline.process_video(video_path, progress_callback)

    print(f"检测到 {len(result.tracks)} 条轨迹")
    for track in result.tracks:
        print(f"  轨迹: 帧 {track.start_frame}-{track.end_frame}, {track.point_count} 点")

    return result

# 运行
asyncio.run(process_video("video.mp4"))
```

---

## 6. 常见问题

### Q1: 模型加载失败

**错误**: `无法导入 BlurBall 模块`

**解决**:
1. 确保 BlurBall 仓库已克隆到 `external/blurball`
2. 检查 `external/blurball/src` 目录是否存在
3. 安装 BlurBall 依赖: `pip install -r external/blurball/requirements.txt`

### Q2: CUDA 内存不足

**错误**: `CUDA out of memory`

**解决**:
1. 减小 `batch_size` (默认 16，可改为 8 或 4)
2. 确保其他 CV 模型已卸载
3. 检查是否有其他进程占用 GPU

### Q3: 检测结果为空

**原因**:
1. 视频中没有乒乓球
2. 检测阈值太高
3. 视频分辨率/格式不支持

**解决**:
1. 降低 `detection_threshold` (默认 0.5，可改为 0.3)
2. 确保视频格式为 mp4/avi/mov/mkv/webm
3. 检查视频内容是否包含乒乓球运动

### Q4: 轨迹断裂

**原因**:
1. 遮挡导致检测丢失
2. `max_gap_frames` 设置太小
3. `max_distance` 设置太小

**解决**:
1. 增大 `max_gap_frames` (默认 5，可改为 10)
2. 增大 `max_distance` (默认 150，可改为 200)

---

## 附录

### A. 参考资料

1. BlurBall 论文: https://arxiv.org/abs/2509.18387
2. HRNet 论文: https://arxiv.org/abs/1908.07919
3. SE-Net 论文: https://arxiv.org/abs/1709.01507

### B. 模型配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `frames_in` | 3 | 输入帧数 |
| `frames_out` | 3 | 输出帧数 |
| `inp_height` | 288 | 输入高度 |
| `inp_width` | 512 | 输入宽度 |
| `score_threshold` | 0.5 | 检测阈值 |
| `max_gap_frames` | 5 | 最大丢失帧数 |
| `max_distance` | 150 | 最大帧间位移 |
| `batch_size` | 16 | 批处理大小 |

### C. 击球类型定义

| 类型 | 英文 | 特征 |
|------|------|------|
| 搓球 | push | 速度慢，弧度低 |
| 削球 | chop | 速度慢，弧度高 |
| 弧圈球 | loop | 速度中等，弧度高 |
| 快攻 | drive | 速度快，弧度低 |
| 扣杀 | smash | 速度极快 |
