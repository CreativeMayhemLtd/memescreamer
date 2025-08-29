# ComfyUI MemescreamerMemoryCleaner

# -*- coding: utf-8 -*-

"""
ComfyUI MemescreamerMemoryCleaner Package

This package provides comprehensive memory management for ComfyUI workflows,
featuring both VRAM and system RAM clearing capabilities with cross-platform support.

Modules:
    memescreamer_memory_cleaner: Main memory management node implementation
"""

__version__ = "1.0.0"
__author__ = "Memescreamer Memory Management"
__description__ = "Comprehensive memory management for ComfyUI workflows"
__license__ = "MIT"

# Package metadata
__all__ = ["memescreamer_memory_cleaner"]

# Import main module components
try:
    from .memescreamer_memory_cleaner import MemescreamerMemoryCleaner
    print("[MemescreamerMemoryCleaner] Package loaded successfully")
except ImportError as e:
    print(f"[MemescreamerMemoryCleaner] Warning: Could not import main module: {e}")

# Version info
VERSION_INFO = {
    "major": 1,
    "minor": 0,
    "patch": 0,
    "release": "stable"
}

def get_version():
    """Return the current version string."""
    return __version__

def get_package_info():
    """Return package information dictionary."""
    return {
        "name": "ComfyUI-MemescreamerMemoryCleaner",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "license": __license__,
        "python_requires": ">=3.8",
        "dependencies": ["torch", "gc", "time", "ctypes", "os"]
    }
