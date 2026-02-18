"""
BlurBall 检测器封装
基于 HRNet 的运动模糊乒乓球检测
"""

import sys
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
import numpy as np
import torch
import torchvision.transforms as T
import cv2
from loguru import logger
from omegaconf import OmegaConf, DictConfig

from app.shared.gpu_manager import GPUManager
from config.settings import get_settings

# 将 BlurBall src 目录添加到路径
BLURBALL_ROOT = Path(__file__).parent.parent.parent.parent / "external" / "blurball"
BLURBALL_SRC = BLURBALL_ROOT / "src"
if str(BLURBALL_SRC) not in sys.path:
    sys.path.insert(0, str(BLURBALL_SRC))


@dataclass
class BallDetection:
    """单帧球检测结果"""
    frame_idx: int
    x: float                    # 中心 x 坐标（原始图像坐标）
    y: float                    # 中心 y 坐标（原始图像坐标）
    confidence: float           # 检测置信度
    blur_angle: Optional[float] = None   # 运动模糊角度（度）
    blur_length: Optional[float] = None  # 运动模糊长度（像素）
    visible: bool = True


class BlurBallDetector:
    """
    BlurBall 检测器
    使用 HRNet backbone 检测运动模糊的乒乓球
    """

    MODEL_NAME = "BlurBall"

    # 默认配置
    DEFAULT_CONFIG = {
        "model": {
            "name": "blurball",
            "frames_in": 3,
            "frames_out": 3,
            "inp_height": 288,
            "inp_width": 512,
            "out_height": 288,
            "out_width": 512,
            "rgb_diff": False,
            "out_scales": [0],
            "MODEL": {
                "EXTRA": {
                    "FINAL_CONV_KERNEL": 1,
                    "PRETRAINED_LAYERS": ["*"],
                    "STEM": {"INPLANES": 64, "STRIDES": [1, 1]},
                    "STAGE1": {
                        "NUM_MODULES": 1,
                        "NUM_BRANCHES": 1,
                        "BLOCK": "BOTTLENECK",
                        "NUM_BLOCKS": [1],
                        "NUM_CHANNELS": [32],
                        "FUSE_METHOD": "SUM",
                    },
                    "STAGE2": {
                        "NUM_MODULES": 1,
                        "NUM_BRANCHES": 2,
                        "BLOCK": "BASIC",
                        "NUM_BLOCKS": [2, 2],
                        "NUM_CHANNELS": [16, 32],
                        "FUSE_METHOD": "SUM",
                    },
                    "STAGE3": {
                        "NUM_MODULES": 1,
                        "NUM_BRANCHES": 3,
                        "BLOCK": "BASIC",
                        "NUM_BLOCKS": [2, 2, 2],
                        "NUM_CHANNELS": [16, 32, 64],
                        "FUSE_METHOD": "SUM",
                    },
                    "STAGE4": {
                        "NUM_MODULES": 1,
                        "NUM_BRANCHES": 4,
                        "BLOCK": "BASIC",
                        "NUM_BLOCKS": [2, 2, 2, 2],
                        "NUM_CHANNELS": [16, 32, 64, 128],
                        "FUSE_METHOD": "SUM",
                    },
                    "DECONV": {
                        "NUM_DECONVS": 0,
                        "KERNEL_SIZE": [],
                        "NUM_BASIC_BLOCKS": 2,
                    },
                },
                "INIT_WEIGHTS": True,
            },
        },
        "detector": {
            "name": "blurball",
            "model_path": None,
            "step": 3,
            "postprocessor": {
                "name": "blurball",
                "score_threshold": 0.5,
                "scales": [0],
                "blob_det_method": "concomp",
                "use_hm_weight": True,
            },
        },
        "tracker": {
            "name": "online_blur",
            "max_disp": 150,
        },
        "runner": {
            "device": "cuda",
            "gpus": [0],
            "vis_result": False,
            "vis_hm": False,
            "vis_traj": False,
        },
    }

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        score_threshold: float = 0.5,
        device: Optional[str] = None,
    ):
        """
        初始化 BlurBall 检测器

        Args:
            checkpoint_path: 模型权重路径
            score_threshold: 检测阈值
            device: 运行设备 ("cuda" 或 "cpu")
        """
        settings = get_settings()

        self.checkpoint_path = checkpoint_path or settings.blurball_checkpoint_path
        self.score_threshold = score_threshold
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self._model = None
        self._detector = None
        self._tracker = None
        self._cfg: Optional[DictConfig] = None
        self._transform = None

        # 图像预处理
        self._preprocess = T.Compose([
            T.ToPILImage(),
            T.Resize((288, 512)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self._is_loaded = False

    def _build_config(self) -> DictConfig:
        """构建 OmegaConf 配置"""
        cfg = OmegaConf.create(self.DEFAULT_CONFIG)
        cfg.detector.model_path = self.checkpoint_path
        cfg.detector.postprocessor.score_threshold = self.score_threshold
        cfg.runner.device = self.device
        return cfg

    def load_model(self) -> None:
        """加载模型到 GPU"""
        if self._is_loaded:
            logger.warning("模型已加载，跳过")
            return

        logger.info(f"加载 BlurBall 模型: {self.checkpoint_path}")

        # 构建配置
        self._cfg = self._build_config()

        # 动态导入 BlurBall 模块
        try:
            from detectors import build_detector
            from trackers import build_tracker
        except ImportError as e:
            logger.error(f"无法导入 BlurBall 模块: {e}")
            logger.error(f"请确保 BlurBall 仓库已克隆到 {BLURBALL_ROOT}")
            raise

        # 构建检测器
        self._detector = build_detector(self._cfg)
        self._tracker = build_tracker(self._cfg)

        self._is_loaded = True
        logger.info("BlurBall 模型加载完成")

    def unload_model(self) -> None:
        """卸载模型，释放显存"""
        if self._detector is not None:
            del self._detector
            self._detector = None
        if self._tracker is not None:
            del self._tracker
            self._tracker = None
        if self._model is not None:
            del self._model
            self._model = None

        self._is_loaded = False
        GPUManager.clear_cache()
        logger.info("BlurBall 模型已卸载")

    def _get_affine_transform(
        self,
        width: int,
        height: int,
    ) -> np.ndarray:
        """计算仿射变换矩阵"""
        from utils.image import get_affine_transform

        c = np.array([width / 2.0, height / 2.0], dtype=np.float32)
        s = max(height, width) * 1.0
        inp_width = self._cfg.model.inp_width
        inp_height = self._cfg.model.inp_height

        trans = np.stack(
            [
                get_affine_transform(c, s, 0, [inp_width, inp_height], inv=1)
                for _ in range(3)
            ],
            axis=0,
        )
        return torch.tensor(trans)[None, :]

    @torch.no_grad()
    def detect_frames(
        self,
        frames: List[np.ndarray],
        frame_indices: Optional[List[int]] = None,
    ) -> List[Optional[BallDetection]]:
        """
        检测多帧中的球

        Args:
            frames: 帧列表 (BGR 格式)
            frame_indices: 帧索引列表

        Returns:
            检测结果列表，每个元素对应一帧
        """
        if not self._is_loaded:
            raise RuntimeError("模型未加载，请先调用 load_model()")

        if len(frames) == 0:
            return []

        if frame_indices is None:
            frame_indices = list(range(len(frames)))

        frames_in = self._cfg.model.frames_in
        step = self._cfg.detector.step

        # 获取图像尺寸
        height, width = frames[0].shape[:2]
        affine_trans = self._get_affine_transform(width, height)

        # 初始化结果
        det_results: Dict[int, List[Dict]] = {idx: [] for idx in frame_indices}
        results: List[Optional[BallDetection]] = [None] * len(frames)

        # 滑动窗口处理
        frames_buffer = []
        indices_buffer = []

        for i, (frame, frame_idx) in enumerate(zip(frames, frame_indices)):
            # 预处理
            frame_tensor = self._preprocess(frame)
            frames_buffer.append(frame_tensor)
            indices_buffer.append(frame_idx)

            if len(frames_buffer) == frames_in:
                # 组合输入
                input_tensor = torch.cat(frames_buffer, dim=0).unsqueeze(0)

                # 运行检测
                batch_results, _ = self._detector.run_tensor(input_tensor, affine_trans)

                # 解析结果
                for eid in batch_results[0].keys():
                    preds = batch_results[0][eid]
                    if eid < len(indices_buffer):
                        det_results[indices_buffer[eid]].extend(preds)

                # 滑动窗口
                if step == 1:
                    frames_buffer.pop(0)
                    indices_buffer.pop(0)
                else:
                    frames_buffer = []
                    indices_buffer = []

        # 运行追踪器整合结果
        self._tracker.refresh()

        for i, frame_idx in enumerate(frame_indices):
            preds = det_results[frame_idx]
            if preds:
                track_result = self._tracker.update(preds)

                if track_result["visi"]:
                    results[i] = BallDetection(
                        frame_idx=frame_idx,
                        x=track_result["x"],
                        y=track_result["y"],
                        confidence=track_result["score"],
                        blur_angle=track_result.get("angle"),
                        blur_length=track_result.get("length"),
                        visible=True,
                    )
                else:
                    results[i] = BallDetection(
                        frame_idx=frame_idx,
                        x=track_result["x"],
                        y=track_result["y"],
                        confidence=0.0,
                        visible=False,
                    )
            else:
                # 无检测，仍然更新追踪器
                track_result = self._tracker.update([])
                results[i] = BallDetection(
                    frame_idx=frame_idx,
                    x=track_result.get("x", -1),
                    y=track_result.get("y", -1),
                    confidence=0.0,
                    visible=False,
                )

        return results

    def detect_single(self, frame: np.ndarray, frame_idx: int = 0) -> Optional[BallDetection]:
        """
        检测单帧中的球（需要配合多帧上下文）

        注意：BlurBall 设计为多帧输入，单帧检测效果可能不佳。
        建议使用 detect_frames 进行批量检测。
        """
        results = self.detect_frames([frame, frame, frame], [frame_idx, frame_idx, frame_idx])
        return results[0] if results else None


def get_detector(
    checkpoint_path: Optional[str] = None,
    score_threshold: Optional[float] = None,
) -> BlurBallDetector:
    """
    获取 BlurBall 检测器实例

    Args:
        checkpoint_path: 模型权重路径
        score_threshold: 检测阈值

    Returns:
        BlurBallDetector 实例
    """
    settings = get_settings()
    return BlurBallDetector(
        checkpoint_path=checkpoint_path or settings.blurball_checkpoint_path,
        score_threshold=score_threshold or settings.ball_tracking_detection_threshold,
    )
