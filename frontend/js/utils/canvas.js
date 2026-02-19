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
    let currentFrame = 0;
    let fps = 30;
    let isPlaying = false;

    // 调整 Canvas 大小
    const resize = () => {
      canvas.width = video.videoWidth || video.clientWidth;
      canvas.height = video.videoHeight || video.clientHeight;
    };

    video.addEventListener('loadedmetadata', resize);
    window.addEventListener('resize', resize);

    // 计算当前帧
    const updateFrame = () => {
      if (video.duration) {
        currentFrame = Math.floor(video.currentTime * fps);
      }
    };

    video.addEventListener('timeupdate', updateFrame);

    return {
      ctx,

      /**
       * 设置轨迹数据
       * @param {Array} trackData - 轨迹数据
       * @param {number} videoFps - 视频帧率
       */
      setTracks(trackData, videoFps = 30) {
        tracks = trackData;
        fps = videoFps;
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

        // 获取当前帧附近的轨迹点
        const frameTrack = tracks.filter(t => {
          return Math.abs(t.frame - currentFrame) <= 15;
        });

        if (frameTrack.length === 0) return;

        // 绘制轨迹线
        ctx.beginPath();
        ctx.strokeStyle = '#1890ff';
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        frameTrack.forEach((point, index) => {
          const x = point.x * canvas.width;
          const y = point.y * canvas.height;

          if (index === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        });

        ctx.stroke();

        // 绘制当前球位置
        const currentPoint = tracks.find(t => t.frame === currentFrame);
        if (currentPoint) {
          const x = currentPoint.x * canvas.width;
          const y = currentPoint.y * canvas.height;

          // 外圈
          ctx.beginPath();
          ctx.arc(x, y, 12, 0, Math.PI * 2);
          ctx.strokeStyle = '#ff4d4f';
          ctx.lineWidth = 2;
          ctx.stroke();

          // 内圈
          ctx.beginPath();
          ctx.arc(x, y, 6, 0, Math.PI * 2);
          ctx.fillStyle = '#ff4d4f';
          ctx.fill();
        }
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
