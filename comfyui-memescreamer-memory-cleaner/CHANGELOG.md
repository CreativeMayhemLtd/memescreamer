# Changelog

All notable changes to ComfyUI MemescreamerMemoryCleaner will be documented in this file.

This component is part of the Creative Mayhem Memescreamer project:
Repository: https://github.com/CreativeMayhemLtd/memescreamer
Location: `comfyui-memescreamer-memory-cleaner/`

## [1.0.0] - 2025-08-30

### Added
- Initial release of MemescreamerMemoryCleaner
- Comprehensive VRAM clearing using CUDA memory management
- System RAM clearing with Windows API integration
- Cross-platform support (Windows, Linux, macOS)
- Configurable memory clearing modes (standard, aggressive, VRAM-only)
- Pass-through node design (images unchanged)
- Detailed console logging for memory usage monitoring
- Error handling with graceful fallbacks
- Dual licensing (CC BY-NC-SA 4.0 for non-commercial, paid for commercial)

### Technical Features
- Multiple CUDA cache clearing passes
- Python garbage collection optimization
- Windows `EmptyWorkingSet` and `SetProcessWorkingSetSize` API integration
- Platform detection and automatic fallback mechanisms
- Memory statistics tracking and reporting
- Configurable wait times between operations

### Performance
- Prevents memory leaks during extended batch processing
- Maintains consistent performance across long sessions
- Minimal processing overhead (0.1-0.3s per operation)
- Enables large-scale batch operations without memory degradation

### Compatibility
- Works with all ComfyUI installations
- Compatible with any PyTorch version
- Supports CUDA-enabled and CPU-only environments
- Full Windows API integration on Windows systems
- Effective fallbacks on Linux and macOS systems
