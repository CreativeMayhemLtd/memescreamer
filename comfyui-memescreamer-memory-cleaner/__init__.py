import sys
import os
import traceback
import importlib.util

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

# Define directory and log path
NODE_DIR = os.path.dirname(__file__)
APP_ROOT = os.path.abspath(os.path.join(NODE_DIR, "..", ".."))
LOG_PATH = os.path.join(APP_ROOT, "output", "memescreamer", "boot_error.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

def try_import(filename, symbol, display):
    path = os.path.join(NODE_DIR, f"{filename}.py")
    if not os.path.exists(path):
        msg = f"❌ {display}: File not found: {path}"
        print(msg)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[ERROR] {msg}\n")
        return

    try:
        spec = importlib.util.spec_from_file_location(symbol, path)
        if spec is None or spec.loader is None:
            msg = f"❌ {display}: Could not load spec for {symbol} from {path}"
            print(msg)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[ERROR] {msg}\n")
            return
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls = getattr(module, symbol)
        NODE_CLASS_MAPPINGS[symbol] = cls
        NODE_DISPLAY_NAME_MAPPINGS[symbol] = f"Memescreamer: {display}"
        print(f"✅ {display}: Loaded {symbol} from {filename}")
    except Exception as e:
        msg = f"❌ {display}: Failed to load {symbol} from {filename} — {e}"
        print(msg)
        print(traceback.format_exc())
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[ERROR] {msg}\n")
            f.write(traceback.format_exc())

# Load the memory cleaner node
try_import("memescreamer_memory_cleaner", "MemescreamerMemoryCleaner", "🧹 Memory Cleaner")
