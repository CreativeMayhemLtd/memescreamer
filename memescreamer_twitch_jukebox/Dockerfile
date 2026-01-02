# Use Python base with CUDA support via pip
# For GPU: Install nvidia-container-toolkit on host and run with --gpus all
FROM python:3.11-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install ffmpeg, git, and dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Clone the Hotdog_NotHotdog NSFW classifier
RUN git clone https://github.com/CreativeMayhemLtd/memescreamer_Hotdog_NotHotdog.git /app/hotdog_nothotdog

# Install PyTorch with CUDA support (auto-detects GPU at runtime)
# This installs the CUDA-capable version that falls back to CPU if no GPU
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Make content filter executable
RUN chmod +x content_filter.sh

# Create directories
RUN mkdir -p /app/media /app/data /app/logs /app/assets

# Create default idle image (solid color)
RUN ffmpeg -f lavfi -i color=c=0x1a1a2e:s=1920x1080:d=1 -frames:v 1 /app/assets/idle.png 2>/dev/null || true

CMD ["python", "main.py"]
