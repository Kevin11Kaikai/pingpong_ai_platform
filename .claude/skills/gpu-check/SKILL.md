# gpu-check

检查 GPU 状态和显存使用情况。

## 使用方式

```
/gpu-check
```

## 执行步骤

1. 运行 `nvidia-smi` 查看 GPU 硬件状态：
   ```bash
   nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits
   ```

2. 运行 Python 检查 PyTorch CUDA 状态：
   ```bash
   python -c "
   import torch
   print('PyTorch version:', torch.__version__)
   print('CUDA available:', torch.cuda.is_available())
   if torch.cuda.is_available():
       print('CUDA version:', torch.version.cuda)
       print('Device name:', torch.cuda.get_device_name(0))
       print('Total memory:', round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2), 'GB')
       print('Allocated:', round(torch.cuda.memory_allocated(0) / 1e9, 2), 'GB')
       print('Cached:', round(torch.cuda.memory_reserved(0) / 1e9, 2), 'GB')
   "
   ```

3. 检查当前加载的模型（如果有）：
   ```bash
   python -c "
   from app.shared.gpu_manager import GPUManager
   info = GPUManager.get_gpu_info()
   print('GPU Info:', info)
   "
   ```

## 预期输出

- GPU: NVIDIA RTX 4080 SUPER
- 显存: 16GB
- CUDA: 12.4
- PyTorch: 2.5.1+cu124

## 显存管理提醒

- CV 模型串行加载，不同时占 GPU
- Embedding 模型常驻内存 (~0.5GB)
- 推理后调用 `torch.cuda.empty_cache()`
- 使用 `GPUManager.load_model()` 上下文管理器
