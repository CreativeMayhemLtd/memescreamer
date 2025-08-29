# ComfyUI MemescreamerMemoryCleaner

A powerful ComfyUI custom node that provides comprehensive memory management for processing workflows, combining aggressive CUDA VRAM clearing with system RAM optimization.

## 🚀 Features

### Dual Memory Management
- **VRAM Clearing**: Aggressive CUDA memory clearing with multiple passes
- **System RAM Clearing**: Platform-optimized clearing (Windows API + cross-platform fallbacks)
- **Comprehensive Cleanup**: Combined approach prevents memory leaks during batch processing

### Performance Benefits
- **Memory Leak Prevention**: Stops RAM accumulation during extended batch operations
- **Sustained Performance**: Maintains consistent processing speeds across long sessions
- **GPU Stability**: Prevents CUDA out-of-memory crashes during intensive workflows
- **Scalable Processing**: Enables large-scale batch operations without degradation

### Production Ready
- **Cross-Platform**: Full functionality on Windows, effective fallbacks on Linux/macOS
- **Zero Workflow Impact**: Pass-through node design (images unchanged)
- **Error Handling**: Graceful fallbacks for all memory operations
- **Backward Compatible**: Works with existing ComfyUI workflows without changes

## 🔧 Installation

### Method 1: Git Clone (Recommended)
```bash
cd ComfyUI/custom_nodes/
git clone https://github.com/CreativeMayhemLtd/memescreamer.git
# Copy the memory cleaner to your custom nodes
cp -r memescreamer/comfyui-memescreamer-memory-cleaner/ ./comfyui-memescreamer-memory-cleaner/
```

### Method 2: Manual Download
1. Download from GitHub: `https://github.com/CreativeMayhemLtd/memescreamer`
2. Copy `comfyui-memescreamer-memory-cleaner/` to `ComfyUI/custom_nodes/`
3. Restart ComfyUI

### Method 3: Direct File Copy
1. Download `memescreamer_memory_cleaner.py` from the repository
2. Place in `ComfyUI/custom_nodes/comfyui-memescreamer-memory-cleaner/`
3. Restart ComfyUI

The node will appear as **"Memescreamer Memory Cleaner"** in the `memescreamer/memory` category.

### Directory Structure
```
ComfyUI/custom_nodes/comfyui-memescreamer-memory-cleaner/
├── memescreamer_memory_cleaner.py  # Main node implementation
├── __init__.py                     # Node registration
└── README.md                       # Documentation
```

## 📋 Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `images` | IMAGE | Required | Input images (pass-through) |
| `force_gc` | Boolean | True | Enable Python garbage collection |
| `clear_cache` | Boolean | True | Clear CUDA memory cache |
| `sync_cuda` | Boolean | True | Synchronize CUDA operations |
| `clear_system_ram` | Boolean | True | Enable system RAM clearing |
| `aggressive_ram_clear` | Boolean | False | Use advanced RAM clearing (Windows API) |
| `wait_ms` | Integer | 100 | Wait time between operations (0-5000ms) |
| `verbose` | Boolean | True | Enable detailed logging |

## 🎯 Usage Examples

### Basic Usage (Recommended)
```
Connect between memory-intensive nodes:
[Video Input] → [Upscaler] → [Memory Cleaner] → [Next Processing Step]

Default settings provide optimal memory management with minimal overhead.
```

### Aggressive Memory Recovery
```
For heavy batch processing:
- Set aggressive_ram_clear: True
- Slightly higher overhead but maximum memory recovery
- Ideal for processing 100+ files in sequence
```

### Legacy VRAM-Only Mode
```
For maximum compatibility:
- Set clear_system_ram: False
- VRAM clearing only (fastest processing)
- Good for simple workflows or testing
```

## ⚙️ Technical Details

### VRAM Management
- Multiple CUDA cache clearing passes
- Memory pool optimization with `torch.cuda.empty_cache()`
- Peak memory statistics reset
- IPC collection for multi-process scenarios

### RAM Management
- **Windows**: `EmptyWorkingSet` + `SetProcessWorkingSetSize` APIs
- **Linux/macOS**: Enhanced Python garbage collection
- **Fallback**: Standard garbage collection on all platforms

### Cross-Platform Compatibility
- **Windows**: Full Windows API integration for maximum performance
- **Linux**: CUDA clearing + garbage collection (highly effective)
- **macOS**: CUDA clearing + garbage collection (works great)

## 🔧 Troubleshooting

### CUDA Warnings
```
NVIDIA GeForce RTX [MODEL] with CUDA capability sm_xxx is not compatible...
```
**Solution**: This is normal behavior. The memory cleaner works regardless of CUDA compatibility warnings.

### Memory Still Accumulating
**Solution**: Enable `aggressive_ram_clear=True` for maximum memory recovery.

### Slower Processing
**Cause**: Memory clearing adds ~0.1-0.3s per operation.  
**Benefit**: Prevents severe slowdowns (minutes) during long sessions.

## 📊 Performance Benchmarks

### Memory Recovery
- **VRAM**: Clears allocated and cached GPU memory completely
- **System RAM**: Significant improvement in sustained performance
- **Processing Impact**: ~0.1-0.3s overhead per operation

### Stability Testing
- **Batch Processing**: Tested with large file collections
- **Extended Sessions**: Prevents memory degradation over time
- **Cross-Platform**: Verified on Windows, Linux, and macOS

## 🛠️ Use Cases

### Video Processing Workflows
- Batch video upscaling with AI models
- Sequential frame processing pipelines
- Large-scale content generation

### Image Processing
- Batch image enhancement
- Style transfer workflows
- High-resolution processing chains

### Development & Testing
- Memory-intensive model testing
- Workflow optimization
- Performance benchmarking

## ⚠️ Requirements

- **ComfyUI**: Compatible with standard ComfyUI installations
- **PyTorch**: Any version (CUDA-enabled recommended for VRAM clearing)
- **Python**: 3.8+ (uses standard library `ctypes` for Windows features)
- **Operating System**: Windows (full features), Linux/macOS (core features)

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional platform optimizations
- Memory pressure detection algorithms
- Adaptive clearing strategies
- Performance monitoring integration

## 📄 License

**Dual License:**
- **Non-Commercial**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
- **Commercial**: Separate paid license required from Creative Mayhem Ltd

For commercial licensing: info@creativemayhem.ltd

## 🙏 Acknowledgments

Developed to solve real-world memory management challenges in production ComfyUI environments. Thanks to the ComfyUI community for testing and feedback.

---

**🎯 Essential for Production Workflows** • **🔧 Cross-Platform Compatible** • **📈 Performance Tested**
