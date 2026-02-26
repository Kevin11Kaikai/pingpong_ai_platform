/**
 * canvas.js - Canvas 绑定工具
 */

const CanvasUtils = {
  /**
   * 初始化 Canvas 叠加层
   * @param {HTMLVideoElement} video - 视频元素
   * @param {HTMLCanvasElement} canvas - Canvas 元素
   * @returns {Object} Canvas 控制器
   */
  initOverlay(video, canvas) {
    const ctx = canvas.getContext('2d');
    let animationId = null;
    let tracks = [];
    let segments = [];       // Track2DResponse 结构化段信息，含速度
    let hoveredSegment = null;
    let currentFrame = 0;
    let fps = 30;
    let isPlaying = false;

    // 调整 Canvas 大小 —— 以视频原生分辨率为坐标系，CSS 负责缩放到显示尺寸
    const resize = () => {
      if (video.videoWidth) {
        canvas.width  = video.videoWidth;
        canvas.height = video.videoHeight;
      } else {
        canvas.width  = video.clientWidth  || 640;
        canvas.height = video.clientHeight || 360;
      }
    };

    // 若 loadedmetadata 已触发（如重新加载历史任务），立即同步一次
    resize();
    video.addEventListener('loadedmetadata', resize);
    window.addEventListener('resize', resize);

    // 计算当前帧
    const updateFrame = () => {
      if (video.duration) {
        currentFrame = Math.floor(video.currentTime * fps);
      }
    };

    video.addEventListener('timeupdate', updateFrame);

    // ── 鼠标悬停：在 canvas 父容器上监听（canvas 自身 pointer-events: none）──
    const container = canvas.parentElement;

    const handleMouseMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      if (!rect.width) return;
      const scaleX = canvas.width  / rect.width;
      const scaleY = canvas.height / rect.height;
      const mx = (e.clientX - rect.left) * scaleX;
      const my = (e.clientY - rect.top)  * scaleY;
      const threshold = 20;           // 命中半径（canvas 原生像素）
      hoveredSegment = null;
      outer: for (const seg of segments) {
        for (const pt of seg.points) {
          if (Math.hypot(pt.x - mx, pt.y - my) < threshold) {
            hoveredSegment = seg;
            break outer;
          }
        }
      }
    };

    const handleMouseLeave = () => { hoveredSegment = null; };

    if (container) {
      container.addEventListener('mousemove', handleMouseMove);
      container.addEventListener('mouseleave', handleMouseLeave);
    }

    // ── 内部绘制辅助函数 ──

    // 圆角矩形（兼容不支持 ctx.roundRect 的浏览器）
    const fillRoundRect = (x, y, w, h, r) => {
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + w - r, y);
      ctx.quadraticCurveTo(x + w, y, x + w, y + r);
      ctx.lineTo(x + w, y + h - r);
      ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      ctx.lineTo(x + r, y + h);
      ctx.quadraticCurveTo(x, y + h, x, y + h - r);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
      ctx.closePath();
      ctx.fill();
    };

    // 速度标签（在当前活跃轨迹段的起点渲染）
    const drawSpeedLabel = (seg) => {
      if (!seg.points.length) return;
      ctx.save();                           // 隔离 ctx 状态，防止污染后续绘制
      const pt = seg.points[0];
      const speed = seg.maxSpeedKmh != null ? seg.maxSpeedKmh.toFixed(1) : '?';
      const label = `#${seg.index} ${speed} km/h`;
      const textColor = seg.isFastest ? '#fa8c16' : '#ffffff';
      const pad = 4;
      ctx.font = 'bold 12px sans-serif';
      const tw = ctx.measureText(label).width;
      const bw = tw + pad * 2;
      const bh = 18;
      // 标签位置：起点右上方，超出画布边界时自动靠内
      let lx = pt.x + 6;
      let ly = pt.y - bh - 6;
      lx = Math.min(Math.max(lx, 2), canvas.width  - bw - 2);
      ly = Math.max(ly, 2);
      // 背景（仅填充一次）
      ctx.fillStyle = 'rgba(0,0,0,0.65)';
      fillRoundRect(lx, ly, bw, bh, 3);
      // 文字
      ctx.fillStyle = textColor;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, lx + pad, ly + bh / 2);
      // 最高速：只描橙色边框，不重复 fill
      if (seg.isFastest) {
        ctx.strokeStyle = '#fa8c16';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(lx + 3, ly);
        ctx.lineTo(lx + bw - 3, ly);
        ctx.quadraticCurveTo(lx + bw, ly, lx + bw, ly + 3);
        ctx.lineTo(lx + bw, ly + bh - 3);
        ctx.quadraticCurveTo(lx + bw, ly + bh, lx + bw - 3, ly + bh);
        ctx.lineTo(lx + 3, ly + bh);
        ctx.quadraticCurveTo(lx, ly + bh, lx, ly + bh - 3);
        ctx.lineTo(lx, ly + 3);
        ctx.quadraticCurveTo(lx, ly, lx + 3, ly);
        ctx.closePath();
        ctx.stroke();
      }
      ctx.restore();
    };

    // 悬停详情框
    const drawHoverTooltip = (seg) => {
      const lines = [
        `轨迹 #${seg.index}`,
        `帧范围: ${seg.startFrame} – ${seg.endFrame}`,
        `检测点: ${seg.pointCount} 个`,
        seg.maxSpeedKmh != null ? `最高速: ${seg.maxSpeedKmh.toFixed(1)} km/h` : null,
        seg.avgSpeedKmh != null ? `平均速: ${seg.avgSpeedKmh.toFixed(1)} km/h` : null,
        seg.durationMs   ? `时长: ${(seg.durationMs / 1000).toFixed(2)} s`   : null,
      ].filter(Boolean);

      const pad  = 8;
      const lineH = 17;
      ctx.font = '12px sans-serif';
      const maxTw = Math.max(...lines.map(l => ctx.measureText(l).width));
      const bw = maxTw + pad * 2;
      const bh = lines.length * lineH + pad * 2;

      const fp = seg.points[0];
      let tx = (fp ? fp.x : 0) + 18;
      let ty = (fp ? fp.y : 0) - bh / 2;
      tx = Math.min(Math.max(tx, 4), canvas.width  - bw - 4);
      ty = Math.min(Math.max(ty, 4), canvas.height - bh - 4);

      ctx.fillStyle = 'rgba(0,0,0,0.82)';
      fillRoundRect(tx, ty, bw, bh, 5);

      ctx.textAlign = 'left';
      ctx.textBaseline = 'top';
      lines.forEach((line, i) => {
        ctx.font = i === 0 ? 'bold 13px sans-serif' : '12px sans-serif';
        ctx.fillStyle = i === 0
          ? (seg.isFastest ? '#fa8c16' : '#faad14')
          : '#ffffff';
        ctx.fillText(line, tx + pad, ty + pad + i * lineH);
      });
    };

    return {
      ctx,

      /**
       * 设置轨迹数据
       * 接受两种格式：
       *   - Track2DResponse[]  ← 后端 /jobs/{id}/tracks 返回格式
       *   - 扁平 point[]       ← 旧格式（向后兼容）
       * @param {Array} trackData - 轨迹数据
       * @param {number} videoFps - 视频帧率
       */
      setTracks(trackData, videoFps = 30) {
        fps = videoFps;
        tracks = [];
        segments = [];
        hoveredSegment = null;

        (trackData || []).forEach((item, idx) => {
          if (Array.isArray(item.points)) {
            // Track2DResponse 结构
            const pts = item.points.map(p => ({ frame: p.frame_idx, x: p.x, y: p.y }));
            pts.forEach(p => tracks.push(p));
            segments.push({
              index:      idx + 1,
              trackId:    item.track_id || item.id || String(idx),
              points:     pts,
              startFrame: item.start_frame ?? (pts[0]?.frame ?? 0),
              endFrame:   item.end_frame   ?? (pts[pts.length - 1]?.frame ?? 0),
              pointCount: item.point_count ?? pts.length,
              durationMs: item.duration_ms ?? 0,
              maxSpeedKmh: null,   // 由 setAnalysis 填充
              avgSpeedKmh: null,
              isFastest:   false,
            });
          } else if (item.frame_idx !== undefined) {
            tracks.push({ frame: item.frame_idx, x: item.x, y: item.y });
          }
        });

        tracks.sort((a, b) => a.frame - b.frame);
      },

      /**
       * 注入每段轨迹的速度分析数据（在 loadResults 拿到数据后调用）
       * @param {Array} analysisData - TrajectoryAnalysisResponse[]
       */
      setAnalysis(analysisData) {
        if (!analysisData || !segments.length) return;
        // 按 track_id 建立索引
        const byId = {};
        for (const a of analysisData) {
          if (a.track_id) byId[a.track_id] = a;
        }
        // 回填速度
        for (const seg of segments) {
          const a = byId[seg.trackId];
          if (a?.speed_stats) {
            seg.maxSpeedKmh = a.speed_stats.max_speed_kmh ?? null;
            seg.avgSpeedKmh = a.speed_stats.avg_speed_kmh ?? null;
          }
        }
        // 标记最高速轨迹（橙色高亮）
        let maxKmh = 0, fastest = null;
        for (const seg of segments) {
          if (seg.maxSpeedKmh != null && seg.maxSpeedKmh > maxKmh) {
            maxKmh = seg.maxSpeedKmh;
            fastest = seg;
          }
        }
        if (fastest) fastest.isFastest = true;
      },

      /**
       * 清除 Canvas
       */
      clear() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      },

      /**
       * 绘制当前帧的轨迹
       */
      drawCurrentFrame() {
        this.clear();

        if (!tracks || tracks.length === 0) return;

        // 取当前帧前后 15 帧的轨迹点作为拖尾
        const trailPoints = tracks.filter(t => {
          const diff = t.frame - currentFrame;
          return diff >= -15 && diff <= 0;          // 显示当前帧及此前 15 帧
        });

        if (trailPoints.length === 0) return;

        // 坐标已是视频原生像素，canvas 分辨率 = video.videoWidth × video.videoHeight
        // CSS 负责将 canvas 缩放到显示尺寸，无需额外换算
        const px = p => p.x;
        const py = p => p.y;

        // 绘制黄色轨迹拖尾
        ctx.beginPath();
        ctx.strokeStyle = '#faad14';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        trailPoints.forEach((point, index) => {
          if (index === 0) {
            ctx.moveTo(px(point), py(point));
          } else {
            ctx.lineTo(px(point), py(point));
          }
        });

        ctx.stroke();

        // 绘制当前帧球位置（最近一个点）
        const latestPoint = trailPoints[trailPoints.length - 1];
        if (latestPoint) {
          const x = px(latestPoint);
          const y = py(latestPoint);

          // 外圈（红色）
          ctx.beginPath();
          ctx.arc(x, y, 12, 0, Math.PI * 2);
          ctx.strokeStyle = '#ff4d4f';
          ctx.lineWidth = 2;
          ctx.stroke();

          // 内圈（红色实心）
          ctx.beginPath();
          ctx.arc(x, y, 6, 0, Math.PI * 2);
          ctx.fillStyle = '#ff4d4f';
          ctx.fill();
        }

        // ── 速度标签：只显示当前帧所属的轨迹段 ──
        for (const seg of segments) {
          if (seg.maxSpeedKmh != null &&
              seg.startFrame <= currentFrame && currentFrame <= seg.endFrame) {
            drawSpeedLabel(seg);
          }
        }

        // ── 悬停详情框 ──
        if (hoveredSegment) drawHoverTooltip(hoveredSegment);
      },

      /**
       * 开始动画
       */
      startAnimation() {
        if (isPlaying) return;
        isPlaying = true;

        const animate = () => {
          if (!isPlaying) return;
          this.drawCurrentFrame();
          animationId = requestAnimationFrame(animate);
        };

        animate();
      },

      /**
       * 停止动画
       */
      stopAnimation() {
        isPlaying = false;
        if (animationId) {
          cancelAnimationFrame(animationId);
          animationId = null;
        }
      },

      /**
       * 绘制落点
       * @param {Array} landingPoints - 落点数据
       */
      drawLandingPoints(landingPoints) {
        if (!landingPoints || landingPoints.length === 0) return;

        landingPoints.forEach((point, index) => {
          const x = point.x * canvas.width;
          const y = point.y * canvas.height;

          // 绘制落点标记
          ctx.beginPath();
          ctx.arc(x, y, 8, 0, Math.PI * 2);
          ctx.fillStyle = point.side === 'left' ? '#52c41a' : '#faad14';
          ctx.fill();

          // 绘制序号
          ctx.fillStyle = '#fff';
          ctx.font = '10px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(String(index + 1), x, y);
        });
      },

      /**
       * 绘制热力图
       * @param {Array} points - 点数据
       * @param {string} colorScheme - 颜色方案
       */
      drawHeatmap(points, colorScheme = 'blue') {
        if (!points || points.length === 0) return;

        const colors = {
          blue: ['#e6f7ff', '#1890ff', '#003a8c'],
          red: ['#fff2f0', '#ff4d4f', '#820014'],
          green: ['#f6ffed', '#52c41a', '#135200'],
        };

        const scheme = colors[colorScheme] || colors.blue;

        // 计算热度
        const gridSize = 20;
        const heatData = {};

        points.forEach(point => {
          const gx = Math.floor(point.x * canvas.width / gridSize);
          const gy = Math.floor(point.y * canvas.height / gridSize);
          const key = `${gx},${gy}`;
          heatData[key] = (heatData[key] || 0) + 1;
        });

        const maxHeat = Math.max(...Object.values(heatData));

        // 绘制热力格子
        Object.entries(heatData).forEach(([key, heat]) => {
          const [gx, gy] = key.split(',').map(Number);
          const intensity = heat / maxHeat;

          const r = Math.round(parseInt(scheme[0].slice(1, 3), 16) * (1 - intensity) +
                               parseInt(scheme[2].slice(1, 3), 16) * intensity);
          const g = Math.round(parseInt(scheme[0].slice(3, 5), 16) * (1 - intensity) +
                               parseInt(scheme[2].slice(3, 5), 16) * intensity);
          const b = Math.round(parseInt(scheme[0].slice(5, 7), 16) * (1 - intensity) +
                               parseInt(scheme[2].slice(5, 7), 16) * intensity);

          ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.6)`;
          ctx.fillRect(gx * gridSize, gy * gridSize, gridSize, gridSize);
        });
      },

      /**
       * 绘制速度箭头
       * @param {number} x - X 坐标 (0-1)
       * @param {number} y - Y 坐标 (0-1)
       * @param {number} speed - 速度值
       * @param {number} angle - 角度（弧度）
       */
      drawSpeedArrow(x, y, speed, angle) {
        const cx = x * canvas.width;
        const cy = y * canvas.height;
        const length = Math.min(50, speed * 2);

        const endX = cx + Math.cos(angle) * length;
        const endY = cy + Math.sin(angle) * length;

        // 绘制箭头线
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(endX, endY);
        ctx.strokeStyle = '#1890ff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // 绘制箭头头部
        const headLength = 10;
        const headAngle = Math.PI / 6;

        ctx.beginPath();
        ctx.moveTo(endX, endY);
        ctx.lineTo(
          endX - headLength * Math.cos(angle - headAngle),
          endY - headLength * Math.sin(angle - headAngle)
        );
        ctx.moveTo(endX, endY);
        ctx.lineTo(
          endX - headLength * Math.cos(angle + headAngle),
          endY - headLength * Math.sin(angle + headAngle)
        );
        ctx.stroke();

        // 绘制速度文本
        ctx.fillStyle = '#1890ff';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`${speed.toFixed(1)} km/h`, endX, endY - 10);
      },

      /**
       * 销毁
       */
      destroy() {
        this.stopAnimation();
        video.removeEventListener('loadedmetadata', resize);
        video.removeEventListener('timeupdate', updateFrame);
        window.removeEventListener('resize', resize);
        if (container) {
          container.removeEventListener('mousemove', handleMouseMove);
          container.removeEventListener('mouseleave', handleMouseLeave);
        }
      },
    };
  },

  /**
   * 截取视频帧
   * @param {HTMLVideoElement} video - 视频元素
   * @returns {string} Data URL
   */
  captureFrame(video) {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    return canvas.toDataURL('image/png');
  },

  /**
   * 下载 Canvas 为图片
   * @param {HTMLCanvasElement} canvas - Canvas 元素
   * @param {string} filename - 文件名
   */
  download(canvas, filename = 'capture.png') {
    const link = document.createElement('a');
    link.download = filename;
    link.href = canvas.toDataURL('image/png');
    link.click();
  },
};

window.CanvasUtils = CanvasUtils;
