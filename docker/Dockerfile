FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

# 安装 Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 3.11 为默认
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt requirements-gpu.txt ./

# 安装依赖
RUN pip3 install --no-cache-dir -r requirements.txt \
    && pip3 install --no-cache-dir -r requirements-gpu.txt

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
