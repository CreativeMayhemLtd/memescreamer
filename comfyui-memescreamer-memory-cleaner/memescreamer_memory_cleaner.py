#!/usr/bin/env python3
"""
MemescreamerMemoryCleaner - Comprehensive Memory Management for ComfyUI
Copyright (c) 2025 Creative Mayhem Ltd. All rights reserved.

DUAL LICENSE TERMS

NON-COMMERCIAL LICENSE:
This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 
International (CC BY-NC-SA 4.0) for non-commercial use.

You are free to:
- Share: copy and redistribute the material in any medium or format
- Adapt: remix, transform, and build upon the material

Under the following terms:
- Attribution: You must give appropriate credit to Creative Mayhem Ltd
- NonCommercial: You may not use the material for commercial purposes
- ShareAlike: If you remix, transform, or build upon the material, you must distribute 
  your contributions under the same license as the original

COMMERCIAL LICENSE:
Commercial use of this software requires a separate paid license from Creative Mayhem Ltd.
Commercial use includes but is not limited to:
- Use in any business or commercial environment
- Use that generates revenue or monetary benefit
- Integration into commercial products or services
- Use by organizations with annual revenue exceeding $100,000

For commercial licensing inquiries, contact:
Creative Mayhem Ltd
Website: http://www.memescreamer.com
Email: licensing@memescreamer.com

DISCLAIMER:
This software is provided "as is" without warranty of any kind, express or implied.
Creative Mayhem Ltd shall not be liable for any damages arising from the use of this software.
"""

import torch
import gc
import time
import ctypes
import os

class MemescreamerMemoryCleaner:
    """
    Comprehensive Memory Management for ComfyUI Workflows
    
    Prevents memory leaks during extended processing by clearing both GPU VRAM 
    and system RAM. Works on all platforms with enhanced features on Windows.
    
    Features:
    • VRAM + System RAM clearing
    • Cross-platform support (Windows API + fallbacks)
    • Pass-through design (images unchanged)
    • Configurable memory clearing modes
    
    Usage: Insert between memory-intensive nodes to prevent accumulation.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {}),
            },
            "optional": {
                "force_gc": ("BOOLEAN", {"default": True}),
                "clear_cache": ("BOOLEAN", {"default": True}),
                "sync_cuda": ("BOOLEAN", {"default": True}),
                "clear_system_ram": ("BOOLEAN", {"default": True}),
                "aggressive_ram_clear": ("BOOLEAN", {"default": False}),
                "wait_ms": ("INT", {"default": 100, "min": 0, "max": 5000}),
                "verbose": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "clear_memory"
    CATEGORY = "memescreamer/memory"
    
    def clear_memory(self, images, force_gc=True, clear_cache=True, sync_cuda=True, clear_system_ram=True, aggressive_ram_clear=False, wait_ms=100, verbose=True):
        """
        Clear both CUDA VRAM and system RAM to prevent memory leaks.
        
        Args:
            images: Input images (passed through unchanged)
            force_gc: Enable Python garbage collection
            clear_cache: Clear CUDA memory cache
            sync_cuda: Synchronize CUDA operations
            clear_system_ram: Enable system RAM clearing
            aggressive_ram_clear: Use advanced RAM clearing (Windows API)
            wait_ms: Wait time between operations (0-5000ms)
            verbose: Enable detailed console logging
            
        Returns:
            Tuple containing the input images unchanged
        """
        try:
            start_time = time.time()
            
            # Get initial memory stats
            if torch.cuda.is_available() and verbose:
                initial_allocated = torch.cuda.memory_allocated() / 1024**3
                initial_cached = torch.cuda.memory_reserved() / 1024**3
                print(f"[MemescreamerMemoryCleaner] Starting comprehensive memory cleaning...")
                print(f"  Initial VRAM - Allocated: {initial_allocated:.2f}GB, Cached: {initial_cached:.2f}GB")
            
            # Step 1: CUDA synchronization
            if sync_cuda and torch.cuda.is_available():
                torch.cuda.synchronize()
            
            # Step 2: Clear CUDA cache aggressively
            if clear_cache and torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                # Additional clearing for memory pools
                if hasattr(torch.cuda, 'memory'):
                    torch.cuda.memory.empty_cache()
                # Reset memory stats
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.reset_accumulated_memory_stats()
            
            # Step 3: Force garbage collection
            if force_gc:
                gc.collect()
                # Multiple passes for stubborn references
                for _ in range(3):
                    gc.collect()
            
            # Step 4: System RAM clearing
            if clear_system_ram:
                self.clear_system_ram_cache(aggressive=aggressive_ram_clear, verbose=verbose)
            
            # Step 5: Optional wait for memory settling
            if wait_ms > 0:
                time.sleep(wait_ms / 1000.0)
            
            # Step 6: Final memory usage reporting
            if torch.cuda.is_available() and verbose:
                final_allocated = torch.cuda.memory_allocated() / 1024**3
                final_cached = torch.cuda.memory_reserved() / 1024**3
                freed_allocated = initial_allocated - final_allocated
                freed_cached = initial_cached - final_cached
                cleanup_time = time.time() - start_time
                
                print(f"[MemescreamerMemoryCleaner] Memory Cleaning Complete:")
                print(f"  VRAM Allocated: {initial_allocated:.2f}GB → {final_allocated:.2f}GB (freed: {freed_allocated:.2f}GB)")
                print(f"  VRAM Cached: {initial_cached:.2f}GB → {final_cached:.2f}GB (freed: {freed_cached:.2f}GB)")
                print(f"  Cleanup time: {cleanup_time:.3f}s")
            
        except Exception as e:
            print(f"[MemescreamerMemoryCleaner] Warning: {e}")
        
        return (images,)
    
    def clear_system_ram_cache(self, aggressive=False, verbose=True):
        """
        Clear system RAM cache using platform-optimized methods.
        
        Args:
            aggressive: Use advanced clearing (Windows API when available)
            verbose: Enable detailed console logging
        """
        try:
            if verbose:
                print(f"  🗑️  Clearing system RAM cache (aggressive={aggressive})...")
            
            # Standard Python garbage collection
            collected = gc.collect()
            
            # Windows-specific RAM clearing
            if os.name == 'nt':  # Windows
                try:
                    # Get Windows API handles
                    kernel32 = ctypes.windll.kernel32
                    psapi = ctypes.windll.psapi
                    
                    # Get current process handle
                    process_handle = kernel32.GetCurrentProcess()
                    
                    if aggressive:
                        # Aggressive: Try to trim working set
                        try:
                            psapi.EmptyWorkingSet(process_handle)
                            if verbose:
                                print(f"    Applied aggressive working set trimming")
                        except Exception as e:
                            if verbose:
                                print(f"    Working set trimming failed: {e}")
                        
                        # Additional aggressive clearing
                        try:
                            kernel32.SetProcessWorkingSetSize(process_handle, -1, -1)
                            if verbose:
                                print(f"    Applied working set size optimization")
                        except Exception as e:
                            if verbose:
                                print(f"    Working set optimization failed: {e}")
                    
                    else:
                        # Standard: Gentle memory pressure
                        try:
                            # Simulate memory pressure to encourage page trimming
                            kernel32.SetProcessWorkingSetSize(process_handle, -1, -1)
                        except:
                            pass
                    
                    if verbose:
                        print(f"    Collected {collected} Python objects + Windows RAM optimization")
                
                except Exception as e:
                    if verbose:
                        print(f"    Windows RAM clearing failed: {e}")
                        print(f"    Fell back to standard garbage collection only")
            
            else:
                # Non-Windows: Standard collection only
                if verbose:
                    print(f"    Non-Windows system: collected {collected} Python objects")
            
        except Exception as e:
            if verbose:
                print(f"  ❌ System RAM clearing error: {e}")
            # Always do at least standard garbage collection
            gc.collect()

# Node registration for ComfyUI
NODE_CLASS_MAPPINGS = {
    "MemescreamerMemoryCleaner": MemescreamerMemoryCleaner
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MemescreamerMemoryCleaner": "Memescreamer Memory Cleaner"
}
